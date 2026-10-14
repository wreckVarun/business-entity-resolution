"""Where does the matcher go wrong? Validation errors by type, with examples.

Reads reports/valid_predictions.parquet (written by train.py) and applies the
saved decision rule. Writes reports/error_analysis.md.

Usage: python src/error_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NORM = ROOT / "data" / "norm"
PQ = ROOT / "data" / "parquet"


def eid_sql(col: str) -> str:
    return f"(CAST(substr({col}, 2, 1) AS BIGINT) * 10000000000 + CAST(substr({col}, 4) AS BIGINT))"


def apply_rule(v: pd.DataFrame, t_top: float, t_more: float) -> pd.DataFrame:
    d = v.sort_values("p", ascending=False).copy()
    d["exclusive"] = ~d.duplicated("t", keep="first")
    e = d[d["exclusive"]].copy()
    e["top"] = ~e.duplicated("s1", keep="first")
    e["pred"] = np.where(e["top"], e["p"] >= t_top, e["p"] >= t_more)
    d = d.merge(e[["s1", "t", "pred"]], on=["s1", "t"], how="left")
    d["pred"] = d["pred"].fillna(False).astype(bool)
    return d


def main() -> None:
    dec = json.loads((ROOT / "models" / "decision.json").read_text())
    v = pd.read_parquet(REPORTS / "valid_predictions.parquet")
    d = apply_rule(v, dec["t_top"], dec["t_more"])
    con = duckdb.connect()
    con.execute("SET threads=10")
    con.register("d", d)
    con.execute(f"""CREATE TABLE rec AS SELECT {eid_sql('entity_id')} eid, entity_id, country, business_name, business_address,
                    name_nonascii, addr_missing, house_no FROM read_parquet(['{NORM / 'train_s1.parquet'}', '{NORM / 'train_s2.parquet'}', '{NORM / 'train_s3.parquet'}'])""")
    con.execute(f"""CREATE TABLE val_s1 AS SELECT DISTINCT s1 FROM d""")
    # blocking misses: true pairs of validation entities that never became candidates
    con.execute(f"""CREATE TABLE gt AS SELECT {eid_sql('source1_entity_id')} s1, {eid_sql('m')} t FROM (
        SELECT source1_entity_id, unnest(string_split(matched_entity_ids, ',')) m FROM '{PQ / 'train_gt.parquet'}'
        WHERE matched_entity_ids IS NOT NULL AND matched_entity_ids <> '')""")
    valid_ids = pd.read_parquet(REPORTS / "valid_predictions.parquet", columns=["s1"]).drop_duplicates()
    con.register("vids", valid_ids)

    def typed(where: str, n: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
        base = f"""
            SELECT a.country, b.name_nonascii AS target_name_nonlatin, b.addr_missing AS target_addr_missing,
                   (a.house_no <> '' AND b.house_no <> '' AND a.house_no <> b.house_no) AS house_no_differs,
                   a.business_name AS s1_name, a.business_address AS s1_address,
                   b.business_name AS target_name, b.business_address AS target_address, x.p
            FROM ({where}) x JOIN rec a ON a.eid = x.s1 JOIN rec b ON b.eid = x.t"""
        allrows = con.execute(base).fetchdf()
        summary = pd.DataFrame({
            "count": [len(allrows)],
            "country_US_share": [round((allrows["country"] == "US").mean(), 3) if len(allrows) else 0],
            "target_name_nonlatin": [round(allrows["target_name_nonlatin"].mean(), 3) if len(allrows) else 0],
            "target_addr_missing": [round(allrows["target_addr_missing"].mean(), 3) if len(allrows) else 0],
            "house_no_differs": [round(allrows["house_no_differs"].mean(), 3) if len(allrows) else 0],
        })
        return summary, allrows.sample(min(n, len(allrows)), random_state=3) if len(allrows) else allrows

    fp_s, fp = typed("SELECT s1, t, p FROM d WHERE pred AND label = 0")
    fn_s, fn = typed("SELECT s1, t, p FROM d WHERE NOT pred AND label = 1")
    bm_s, bm = typed("""SELECT g.s1, g.t, NULL::DOUBLE p FROM gt g SEMI JOIN vids ON vids.s1 = g.s1
                        ANTI JOIN d ON d.s1 = g.s1 AND d.t = g.t""")
    tp = int((d["pred"] & (d["label"] == 1)).sum())

    def md_table(df: pd.DataFrame) -> str:
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in cols) + " |")
        return "\n".join(lines)

    ex_cols = ["country", "s1_name", "s1_address", "target_name", "target_address", "p"]
    out = [
        "# Error analysis (validation)",
        "",
        f"Decision rule: best candidate if p >= {dec['t_top']}, further candidates if p >= {dec['t_more']}, "
        "each Source 2/3 record given to one Source 1 entity at most.",
        "",
        f"Correct links: {tp:,}. False links: {len(fp) and int(fp_s['count'][0]):,}. "
        f"Missed links among candidates: {int(fn_s['count'][0]):,}. True links lost in blocking: {int(bm_s['count'][0]):,}.",
        "",
        "## False links (predicted match, not a match)", "", md_table(fp_s), "", md_table(fp[ex_cols].round(3)), "",
        "## Missed links that were candidates", "", md_table(fn_s), "", md_table(fn[ex_cols].round(3)), "",
        "## True links lost in blocking", "", md_table(bm_s), "", md_table(bm[ex_cols[:-1]]), "",
    ]
    (REPORTS / "error_analysis.md").write_text("\n".join(out))
    print("\n".join(out[:8]))
    print("false links:", fp_s.to_dict("records"))
    print("missed (candidates):", fn_s.to_dict("records"))
    print("blocking misses:", bm_s.to_dict("records"))


if __name__ == "__main__":
    main()
