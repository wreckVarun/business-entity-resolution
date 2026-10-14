"""Train the LightGBM pair classifier and tune the decision rule for entity F0.5.

Validation is grouped by Source 1 entity: 20% of the sampled entities (and all
of their candidate pairs) are held out, so the model is never scored on an
entity it trained on. Entities whose true matches were all lost in blocking
are still counted, so the score includes blocking misses.

Decision rule on model probabilities p:
  1. exclusivity: every Source 2/3 record belongs to at most one Source 1 entity
     in the training labels, so a record is only kept for the Source 1 entity
     that gives it the highest p
  2. per Source 1 entity, the best remaining candidate is a match if p >= t_top,
     any further candidate if p >= t_more
Both thresholds are chosen by maximising mean entity F0.5 on the validation set.

Usage:
  python src/train.py            # train + validate + save model and decision rule
  python src/train.py --loco     # leave-one-country-out check (proxy for the unseen country)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FEAT = ROOT / "data" / "features" / "train"
PQ = ROOT / "data" / "parquet"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"

ID_COLS = ["s1", "t", "label"]

PARAMS = dict(
    objective="binary",
    learning_rate=0.1,
    num_leaves=255,
    min_data_in_leaf=500,
    feature_fraction=0.7,
    bagging_fraction=0.5,
    bagging_freq=1,
    lambda_l2=1.0,
    max_bin=63,
    num_threads=10,
    verbose=-1,
)


def eid_sql(col: str) -> str:
    return f"(CAST(substr({col}, 2, 1) AS BIGINT) * 10000000000 + CAST(substr({col}, 4) AS BIGINT))"


# ------------------------------------------------------------------ data --

def parts() -> list[Path]:
    return sorted(FEAT.glob("part-*.parquet"))


def feature_names() -> list[str]:
    names = pq.read_schema(parts()[0]).names
    return [c for c in names if c not in ID_COLS]


def load_ids(extra: tuple[str, ...] = ()) -> pd.DataFrame:
    cols = ID_COLS + list(extra)
    return pd.concat([pq.read_table(f, columns=cols).to_pandas() for f in parts()], ignore_index=True)


EASY_KEEP = 0.25  # share of easy non-matches kept for training (weighted back up by 1/EASY_KEEP)


def training_rows(ids: pd.DataFrame, allowed: np.ndarray, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Mask of training rows and their weights. Keeps every match and every hard non-match
    (top-10 candidate of its Source 1 entity, or top-2 competitor for its target); easy
    non-matches are sampled at EASY_KEEP and weighted 1/EASY_KEEP so probabilities stay calibrated."""
    rng = np.random.default_rng(seed)
    hard = (ids["label"].to_numpy() == 1) | (ids["rnk"].to_numpy() <= 10) | (ids["t_rank"].to_numpy() <= 2)
    keep = allowed & (hard | (rng.random(len(ids)) < EASY_KEEP))
    w = np.where(hard, 1.0, 1.0 / EASY_KEEP)[keep].astype(np.float32)
    return keep, w


def load_matrix(feats: list[str], mask: np.ndarray) -> np.ndarray:
    """Rows where mask is True, as one float32 matrix, filled part by part (no full copy)."""
    out = np.empty((int(mask.sum()), len(feats)), dtype=np.float32)
    pos = start = 0
    for f in parts():
        n = pq.read_metadata(f).num_rows
        m = mask[start:start + n]
        k = int(m.sum())
        if k:
            tbl = pq.read_table(f, columns=feats)
            for j, c in enumerate(feats):
                col = tbl.column(c).to_numpy(zero_copy_only=False)
                out[pos:pos + k, j] = col[m]
            pos += k
        start += n
    return out


def sampled_s1() -> pd.DataFrame:
    """Every training Source 1 entity in the feature sample (with country), including
    entities that got no candidates at all."""
    meta = json.loads((FEAT / "_meta.json").read_text())
    con = duckdb.connect()
    return con.execute(f"""
        SELECT {eid_sql('entity_id')} s1, country FROM '{PQ / 'train_s1.parquet'}'
        WHERE hash({eid_sql('entity_id')}) % 1000 < {meta['sample_per_mille']}""").fetchdf()


def n_true(s1_ids: np.ndarray) -> np.ndarray:
    """Number of true matches for each given Source 1 id."""
    con = duckdb.connect()
    con.register("ids", pd.DataFrame({"s1": s1_ids, "pos": np.arange(len(s1_ids))}))
    df = con.execute(f"""
        SELECT ids.pos, CASE WHEN g.matched_entity_ids IS NULL OR g.matched_entity_ids = '' THEN 0
                             ELSE len(string_split(g.matched_entity_ids, ',')) END n
        FROM ids JOIN '{PQ / 'train_gt.parquet'}' g ON {eid_sql('g.source1_entity_id')} = ids.s1
        ORDER BY ids.pos""").fetchdf()
    assert len(df) == len(s1_ids)
    return df["n"].to_numpy()


# -------------------------------------------------------------- decision --

class Grid:
    """Fast evaluation of the two-threshold decision rule for many threshold pairs."""

    def __init__(self, s1: np.ndarray, t: np.ndarray, label: np.ndarray, p: np.ndarray,
                 entity_ids: np.ndarray, entity_n_true: np.ndarray):
        d = pd.DataFrame({"s1": s1, "t": t, "y": label, "p": p})
        # exclusivity: keep each target only for its most likely Source 1 entity
        d = d.sort_values("p", ascending=False).drop_duplicates("t", keep="first")
        d["top"] = ~d.duplicated("s1", keep="first")  # already sorted by p: first row per s1 is its best
        index = pd.Series(np.arange(len(entity_ids)), index=entity_ids)
        self.ent = index.loc[d["s1"].to_numpy()].to_numpy()
        self.p = d["p"].to_numpy()
        self.y = d["y"].to_numpy().astype(np.int64)
        self.top = d["top"].to_numpy()
        self.n_true = entity_n_true.astype(np.float64)
        self.n_ent = len(entity_ids)

    def evaluate(self, t_top: float, t_more: float) -> dict:
        keep = np.where(self.top, self.p >= t_top, self.p >= t_more)
        pred = np.bincount(self.ent[keep], minlength=self.n_ent).astype(np.float64)
        tp = np.bincount(self.ent[keep], weights=self.y[keep], minlength=self.n_ent)
        nt = self.n_true
        with np.errstate(divide="ignore", invalid="ignore"):
            prec = np.where(pred > 0, tp / pred, 0.0)
            rec = np.where(nt > 0, tp / nt, 0.0)
            f = np.where(tp > 0, 1.25 * prec * rec / (0.25 * prec + rec), 0.0)
        f = np.where(nt == 0, (pred == 0).astype(np.float64), f)
        return {"t_top": round(float(t_top), 3), "t_more": round(float(t_more), 3), "f05": float(f.mean()),
                "precision": float(prec[pred > 0].mean()), "recall": float(rec[nt > 0].mean()),
                "predicted_links": int(pred.sum())}

    def search(self) -> tuple[dict, list[dict]]:
        grid = np.round(np.arange(0.05, 0.96, 0.025), 3)
        rows = [self.evaluate(a, b) for a in grid for b in grid if b >= a]
        return max(rows, key=lambda r: r["f05"]), rows


# ---------------------------------------------------------------- models --

def dataset(x: np.ndarray, y: np.ndarray, feats: list[str], w: np.ndarray | None = None, reference=None) -> lgb.Dataset:
    d = lgb.Dataset(x, label=y, weight=w, feature_name=feats, reference=reference,
                    params={"max_bin": PARAMS["max_bin"], "verbose": -1}, free_raw_data=True)
    return d.construct()


def fit(dtr: lgb.Dataset, dva: lgb.Dataset | None = None, rounds: int = 2000) -> lgb.Booster:
    if dva is None:
        return lgb.train(PARAMS, dtr, num_boost_round=rounds)
    return lgb.train(PARAMS, dtr, num_boost_round=rounds, valid_sets=[dva],
                     callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(50)])


def main_holdout() -> None:
    t0 = time.time()
    import gc
    feats = feature_names()
    ids = load_ids(("rnk", "t_rank"))
    ents = sampled_s1()
    valid_ents = ents.sample(frac=0.2, random_state=42)
    is_val = ids["s1"].isin(set(valid_ents["s1"])).to_numpy()
    tr_mask, w_tr = training_rows(ids, ~is_val)
    print(f"{len(ids):,} pairs ({ids['label'].mean():.3f} positive), {len(feats)} features; "
          f"train rows after sampling easy non-matches: {tr_mask.sum():,}; "
          f"valid: {is_val.sum():,} pairs / {len(valid_ents):,} entities", flush=True)

    dtr = dataset(load_matrix(feats, tr_mask), ids["label"].to_numpy()[tr_mask], feats, w_tr)
    gc.collect()
    x_va = load_matrix(feats, is_val)
    dva = dataset(x_va.copy(), ids["label"].to_numpy()[is_val], feats, reference=dtr)
    gc.collect()
    print(f"datasets built ({time.time() - t0:.0f}s)", flush=True)

    t = time.time()
    model = fit(dtr, dva)
    del dtr, dva
    gc.collect()
    print(f"trained {model.best_iteration} rounds in {time.time() - t:.0f}s", flush=True)
    p = model.predict(x_va, num_iteration=model.best_iteration)

    v = ids.loc[is_val, ["s1", "t", "label"]].reset_index(drop=True)
    ent_ids = valid_ents["s1"].to_numpy()
    nt = n_true(ent_ids)
    grid = Grid(v["s1"].to_numpy(), v["t"].to_numpy(), v["label"].to_numpy(), p, ent_ids, nt)
    best, rows = grid.search()
    single = max((r for r in rows if r["t_top"] == r["t_more"]), key=lambda r: r["f05"])
    ceiling = Grid(v["s1"].to_numpy(), v["t"].to_numpy(), v["label"].to_numpy(), v["label"].to_numpy().astype(float),
                   ent_ids, nt).evaluate(0.5, 0.5)

    # per-country breakdown at the chosen thresholds
    by_country = {}
    for c in sorted(valid_ents["country"].unique()):
        sel = valid_ents["country"].to_numpy() == c
        cs = set(ent_ids[sel])
        m = v["s1"].isin(cs).to_numpy()
        g = Grid(v["s1"].to_numpy()[m], v["t"].to_numpy()[m], v["label"].to_numpy()[m], p[m], ent_ids[sel], nt[sel])
        by_country[c] = {k: round(val, 4) if isinstance(val, float) else val
                         for k, val in g.evaluate(best["t_top"], best["t_more"]).items()}

    print(f"VALID F0.5 {best['f05']:.4f} (precision {best['precision']:.4f}, recall {best['recall']:.4f}) "
          f"at t_top={best['t_top']}, t_more={best['t_more']}")
    print(f"  single threshold {single['t_top']}: F0.5 {single['f05']:.4f}")
    print(f"  blocking ceiling (perfect classifier on these candidates): F0.5 {ceiling['f05']:.4f}")
    print(f"  by country: {by_country}")

    imp = pd.Series(model.feature_importance("gain"), index=feats).sort_values(ascending=False)
    REPORTS.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    report = {
        "valid_entities": int(len(ent_ids)), "valid_pairs": int(is_val.sum()), "train_pairs": int((~is_val).sum()),
        "best_iteration": int(model.best_iteration),
        "best": best, "single_threshold": single, "blocking_ceiling": ceiling, "by_country": by_country,
        "feature_importance_gain": {k: round(float(x), 5) for k, x in (imp / imp.sum()).items()},
        "threshold_grid": rows,
    }
    (REPORTS / "validation.json").write_text(json.dumps(report, indent=2))
    v.assign(p=p).to_parquet(REPORTS / "valid_predictions.parquet")
    model.save_model(str(MODELS / "lgbm_matcher.txt"), num_iteration=model.best_iteration)
    (MODELS / "decision.json").write_text(json.dumps(
        {"t_top": best["t_top"], "t_more": best["t_more"], "features": feats}, indent=2))
    print(f"saved models/lgbm_matcher.txt ({time.time() - t0:.0f}s total)")


def main_loco() -> None:
    """Train without one country, evaluate on it; compare with a model that saw that country."""
    feats = feature_names()
    ids = load_ids()
    ents = sampled_s1()
    country = dict(zip(ents["s1"], ents["country"]))
    pair_country = ids["s1"].map(country).to_numpy()
    rng = np.random.default_rng(7)
    dec = json.loads((MODELS / "decision.json").read_text())
    results = []
    for held in ("India", "US"):
        held_ents = ents[ents["country"] == held].sample(n=40_000, random_state=7)
        eval_mask = ids["s1"].isin(set(held_ents["s1"])).to_numpy()
        x_ev = load_matrix(feats, eval_mask)
        v = ids.loc[eval_mask].reset_index(drop=True)
        nt = n_true(held_ents["s1"].to_numpy())
        row = {"held_out_country": held, "eval_entities": len(held_ents)}
        # same training size for both variants: 4M pairs drawn from the allowed pool
        for tag, pool in (("trained_without_it", (pair_country != held) & ~eval_mask),
                          ("trained_with_it", ~eval_mask)):
            idx = np.flatnonzero(pool)
            take = np.zeros(len(ids), dtype=bool)
            take[rng.choice(idx, size=min(len(idx), 4_000_000), replace=False)] = True
            m = fit(dataset(load_matrix(feats, take), ids["label"].to_numpy()[take], feats), rounds=600)
            p = m.predict(x_ev)
            g = Grid(v["s1"].to_numpy(), v["t"].to_numpy(), v["label"].to_numpy(), p, held_ents["s1"].to_numpy(), nt)
            best, _ = g.search()
            # thresholds tuned on the held-out country's own labels (optimistic) ...
            row[tag] = {k: round(val, 4) if isinstance(val, float) else val for k, val in best.items()}
            # ... and at the main model's thresholds, as when predicting a country without labels (France)
            fixed = g.evaluate(dec["t_top"], dec["t_more"])
            row[tag + "_main_thresholds"] = {k: round(val, 4) if isinstance(val, float) else val for k, val in fixed.items()}
            print(held, tag, row[tag], "| main thresholds:", row[tag + "_main_thresholds"], flush=True)
        results.append(row)
    (REPORTS / "leave_one_country_out.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loco", action="store_true")
    a = ap.parse_args()
    main_loco() if a.loco else main_holdout()
