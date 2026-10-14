"""Pairwise features for candidate pairs.

For every (Source 1 record, candidate Source 2/3 record) pair from blocking we
compute ~50 numbers describing how alike the two records are. Nothing uses
the country label as a category, so the same features work for France.

Three groups:
  1. string similarity (RapidFuzz, C++, multithreaded): names, phonetic names,
     names without spaces, 'trading as' variants, addresses
  2. IDF-weighted word overlap and house-number agreement (DuckDB list ops)
  3. context: how this candidate ranks among all candidates of the same Source 1
     record, and how many Source 1 records compete for the same target

Usage: python src/features.py train|test [top_k] [s1_sample_fraction]
Output: data/features/{split}/part-*.parquet
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from rapidfuzz import distance, fuzz, process

ROOT = Path(__file__).resolve().parents[1]
NORM = ROOT / "data" / "norm"
WORK = ROOT / "data" / "work"
FEAT = ROOT / "data" / "features"

BLOCK_KINDS = ["nc", "np", "ab", "nca", "npa", "nf", "pf", "ns", "nh", "ah"]
PAIRS_PER_CHUNK = 1_100_000
WORKERS = -1


def eid(col: str = "entity_id") -> str:
    return f"(CAST(substr({col}, 2, 1) AS BIGINT) * 10000000000 + CAST(substr({col}, 4) AS BIGINT))"


def connect(split: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(WORK / f"{split}_features.duckdb"))
    threads, mem = os.environ.get("ER_THREADS", "8"), os.environ.get("ER_MEMORY", "6GB")
    con.execute(f"SET threads={threads}; SET memory_limit='{mem}'; SET temp_directory='{WORK / 'tmp'}'; "
                "SET preserve_insertion_order=false")
    return con


def build_records(con, split: str) -> None:
    """One row per record with word lists and per-word IDF (computed within country)."""
    files = [str(NORM / f"{split}_s{i}.parquet") for i in (1, 2, 3)]
    con.execute(f"""CREATE OR REPLACE TABLE rec AS
        SELECT {eid()} eid, entity_id, country, src, name_norm, name_core, coalesce(name_alt, '') name_alt, name_phon,
               addr_norm, addr_words, addr_nums, house_no, name_nonascii, addr_nonascii, addr_missing,
               list_distinct(list_filter(string_split(name_core, ' '), lambda x: length(x) > 0)) nw,
               list_distinct(list_filter(string_split(name_phon, ' '), lambda x: length(x) > 0)) pw,
               list_distinct(list_filter(string_split(addr_words, ' '), lambda x: length(x) > 0)) aw,
               list_distinct(list_filter(string_split(addr_nums, ' '), lambda x: length(x) > 0)) an,
               list_distinct(list_filter(list_transform(regexp_extract_all(addr_nums, '[0-9]+'),
                   lambda y: TRY_CAST(y AS BIGINT)), lambda z: z IS NOT NULL)) ints,
               TRY_CAST(nullif(regexp_extract(house_no, '[0-9]+'), '') AS BIGINT) hn_base
        FROM read_parquet({files})""")
    for col in ("nw", "pw", "aw"):
        con.execute(f"""CREATE OR REPLACE TABLE idf_{col} AS
            WITH t AS (SELECT country, unnest({col}) w FROM rec),
                 n AS (SELECT country, count(*) n FROM rec GROUP BY 1)
            SELECT country, w, ln(n.n * 1.0 / count(*)) idf FROM t JOIN n USING (country) GROUP BY country, w, n.n""")
        # (record, word, idf) rows; shared-word weights are computed per chunk of pairs with joins
        con.execute(f"""CREATE OR REPLACE TABLE tw_{col} AS
            SELECT x.eid, x.w, i.idf FROM (SELECT eid, country, unnest({col}) w FROM rec) x
            JOIN idf_{col} i USING (country, w) ORDER BY x.eid""")
        con.execute(f"CREATE OR REPLACE TABLE tot_{col} AS SELECT eid, sum(idf) tot FROM tw_{col} GROUP BY eid")


def build_context(con, split: str, top_k: int, frac: float) -> int:
    """Candidates (top_k per S1), optional S1 sample, labels and ranking context. Returns the chunk count."""
    cands = WORK / f"{split}_cands.parquet"
    sample = f"AND hash(s1) % 1000 < {int(frac * 1000)}" if frac < 1 else ""
    con.execute(f"""CREATE OR REPLACE TABLE c AS SELECT * FROM '{cands}' WHERE rnk <= {top_k} {sample}""")
    n_chunks = max(1, -(-con.execute("SELECT count(*) FROM c").fetchone()[0] // PAIRS_PER_CHUNK))
    if split == "train":
        con.execute(f"""CREATE OR REPLACE TABLE gt AS
            SELECT {eid('source1_entity_id')} s1, {eid('m')} t FROM (
              SELECT source1_entity_id, unnest(string_split(matched_entity_ids, ',')) m
              FROM '{ROOT / 'data' / 'parquet' / 'train_gt.parquet'}'
              WHERE matched_entity_ids IS NOT NULL AND matched_entity_ids <> '')""")
        label = "(gt.t IS NOT NULL)::TINYINT AS label"
        join = "LEFT JOIN gt ON gt.s1 = c.s1 AND gt.t = c.t"
    else:
        label, join = "NULL::TINYINT AS label", ""
    kind_bits = ", ".join(f"((c.kinds >> {i}) & 1)::TINYINT AS k_{k}" for i, k in enumerate(BLOCK_KINDS))
    # context features: ranking of this pair among the candidates of its S1 and of its target.
    # The target-side view uses all candidates of the full split, not just the sample.
    # Window functions over tens of millions of rows do not fit in memory at once, so they run in
    # slices: target-level context sliced by target, entity-level context sliced by Source 1 entity.
    slices = 8
    con.execute("""CREATE OR REPLACE TABLE tctx (s1 BIGINT, t BIGINT, t_n_s1 BIGINT, t_rank BIGINT, t_score_rel DOUBLE)""")
    for m in range(slices):
        con.execute(f"""INSERT INTO tctx
            SELECT s1, t,
                   count(*) OVER (PARTITION BY t) t_n_s1,
                   row_number() OVER (PARTITION BY t ORDER BY score DESC, s1) t_rank,
                   score / max(score) OVER (PARTITION BY t) t_score_rel
            FROM '{cands}' WHERE rnk <= {top_k} AND hash(t) % {slices} = {m}""")
    con.execute("DROP TABLE IF EXISTS pairs")
    for m in range(slices):
        verb = "CREATE TABLE pairs AS" if m == 0 else "INSERT INTO pairs"
        con.execute(f"""{verb}
            SELECT c.s1, c.t, c.score, c.n_keys, c.rnk, {label},
                   {kind_bits}, bit_count(c.kinds)::TINYINT n_kinds,
                   count(*) OVER (PARTITION BY c.s1) s1_n_cands,
                   c.score / max(c.score) OVER (PARTITION BY c.s1) s1_score_rel,
                   c.score - max(c.score) OVER (PARTITION BY c.s1) s1_score_gap,
                   x.t_n_s1, x.t_rank, x.t_score_rel,
                   hash(c.s1) % {n_chunks} AS chunk
            FROM (SELECT * FROM c WHERE hash(s1) % {slices} = {m}) c {join}
            JOIN tctx x ON x.s1 = c.s1 AND x.t = c.t""")
    return n_chunks


SQL_SHARED = """
CREATE OR REPLACE TEMP TABLE sh_{col} AS
SELECT pc.s1, pc.t, sum(a.idf) shared
FROM pc JOIN tw_{col} a ON a.eid = pc.s1 JOIN tw_{col} b ON b.eid = pc.t AND b.w = a.w
GROUP BY pc.s1, pc.t
"""

SQL_CHUNK = """
SELECT p.* EXCLUDE (chunk),
  a.name_norm a_name_norm, b.name_norm b_name_norm, a.name_core a_core, b.name_core b_core,
  a.name_alt a_alt, b.name_alt b_alt, a.name_phon a_phon, b.name_phon b_phon,
  a.addr_norm a_addr, b.addr_norm b_addr, a.addr_words a_aw_s, b.addr_words b_aw_s,
  b.src b_src, b.name_nonascii b_name_nonascii, b.addr_nonascii b_addr_nonascii, b.addr_missing b_addr_missing,
  len(a.nw) a_n_words, len(b.nw) b_n_words, length(a.name_core) a_name_len, length(b.name_core) b_name_len,
  len(a.aw) a_n_aw, len(b.aw) b_n_aw,
  -- IDF-weighted overlap of name words, phonetic words and address words
  coalesce(snw.shared, 0) nw_shared, tna.tot a_nw_tot, tnb.tot b_nw_tot,
  coalesce(spw.shared, 0) pw_shared, tpa.tot a_pw_tot, tpb.tot b_pw_tot,
  coalesce(saw.shared, 0) aw_shared, taa.tot a_aw_tot, tab.tot b_aw_tot,
  -- house numbers
  (a.house_no <> '' AND a.house_no = b.house_no)::TINYINT house_eq,
  (a.house_no <> '')::TINYINT a_has_num, (b.house_no <> '')::TINYINT b_has_num,
  len(list_intersect(a.an, b.an)) num_shared,
  (len(a.an) > 0 AND len(b.an) > 0 AND len(list_intersect(a.an, b.an)) = 0)::TINYINT num_conflict,
  (a.house_no <> '' AND list_contains(b.an, a.house_no))::TINYINT a_house_in_b,
  -- house numbers as integers: tolerant to leading zeros (00419), suffixes (3008-A) and ranges (637-641)
  (a.hn_base IS NOT NULL AND a.hn_base = b.hn_base)::TINYINT hn_base_eq,
  CASE WHEN a.hn_base IS NULL OR b.hn_base IS NULL THEN NULL
       ELSE ln(1 + abs(CAST(a.hn_base AS DOUBLE) - CAST(b.hn_base AS DOUBLE))) END hn_absdiff_log,
  len(list_intersect(a.ints, b.ints)) ints_shared,
  (len(a.ints) > 0 AND len(b.ints) > 0 AND len(list_intersect(a.ints, b.ints)) = 0)::TINYINT ints_conflict,
  (a.hn_base IS NOT NULL AND list_contains(b.ints, a.hn_base))::TINYINT a_hn_in_b_ints,
  (b.hn_base IS NOT NULL AND list_contains(a.ints, b.hn_base))::TINYINT b_hn_in_a_ints,
  (a.addr_words <> '' AND a.addr_words = b.addr_words)::TINYINT addr_words_eq
FROM pc p
JOIN rec a ON a.eid = p.s1 JOIN rec b ON b.eid = p.t
LEFT JOIN sh_nw snw ON snw.s1 = p.s1 AND snw.t = p.t
LEFT JOIN sh_pw spw ON spw.s1 = p.s1 AND spw.t = p.t
LEFT JOIN sh_aw saw ON saw.s1 = p.s1 AND saw.t = p.t
LEFT JOIN tot_nw tna ON tna.eid = p.s1 LEFT JOIN tot_nw tnb ON tnb.eid = p.t
LEFT JOIN tot_pw tpa ON tpa.eid = p.s1 LEFT JOIN tot_pw tpb ON tpb.eid = p.t
LEFT JOIN tot_aw taa ON taa.eid = p.s1 LEFT JOIN tot_aw tab ON tab.eid = p.t
"""


def _cp(a, b, scorer) -> np.ndarray:
    return process.cpdist(a, b, scorer=scorer, workers=WORKERS, dtype=np.float32)


def _best_alt(df: pd.DataFrame) -> np.ndarray:
    """Best token-set similarity over 'trading as' variants of either side."""
    base = df["f_name_tset"].to_numpy().copy()
    rows, a_s, b_s = [], [], []
    for side_alt, other_core, swap in (("b_alt", "a_core", False), ("a_alt", "b_core", True)):
        has = df[side_alt].to_numpy() != ""
        for i in np.flatnonzero(has):
            for v in df[side_alt].iat[i].split("|"):
                rows.append(i)
                a_s.append(df[other_core].iat[i])
                b_s.append(v)
    if rows:
        sims = _cp(a_s, b_s, fuzz.token_set_ratio)
        np.maximum.at(base, np.array(rows), sims)
    return base


def string_features(df: pd.DataFrame) -> pd.DataFrame:
    f = {}
    a_core, b_core = df["a_core"].tolist(), df["b_core"].tolist()
    f["f_name_ratio"] = _cp(df["a_name_norm"].tolist(), df["b_name_norm"].tolist(), fuzz.ratio)
    f["f_name_tsort"] = _cp(a_core, b_core, fuzz.token_sort_ratio)
    f["f_name_tset"] = _cp(a_core, b_core, fuzz.token_set_ratio)
    f["f_name_partial"] = _cp(a_core, b_core, fuzz.partial_ratio)
    f["f_name_jw"] = _cp(a_core, b_core, distance.JaroWinkler.normalized_similarity)
    f["f_name_nospace"] = _cp([s.replace(" ", "") for s in a_core], [s.replace(" ", "") for s in b_core], fuzz.ratio)
    a_ph, b_ph = df["a_phon"].tolist(), df["b_phon"].tolist()
    f["f_phon_ratio"] = _cp(a_ph, b_ph, fuzz.ratio)
    f["f_phon_tset"] = _cp(a_ph, b_ph, fuzz.token_set_ratio)
    a_ad, b_ad = df["a_addr"].tolist(), df["b_addr"].tolist()
    f["f_addr_ratio"] = _cp(a_ad, b_ad, fuzz.ratio)
    f["f_addr_tset"] = _cp(a_ad, b_ad, fuzz.token_set_ratio)
    f["f_addr_tsort"] = _cp(a_ad, b_ad, fuzz.token_sort_ratio)
    a_aw, b_aw = df["a_aw_s"].tolist(), df["b_aw_s"].tolist()
    f["f_addrw_tset"] = _cp(a_aw, b_aw, fuzz.token_set_ratio)
    f["f_addrw_partial"] = _cp(a_aw, b_aw, fuzz.partial_ratio)
    out = pd.DataFrame(f, index=df.index)
    df = pd.concat([df, out], axis=1)
    df["f_name_alt_best"] = _best_alt(df)
    return df


def derived(df: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-9
    for k in ("nw", "pw", "aw"):
        sh, ta, tb = df[f"{k}_shared"], df[f"a_{k}_tot"].fillna(0), df[f"b_{k}_tot"].fillna(0)
        df[f"{k}_cont_a"] = sh / (ta + eps)          # share of A's word weight found in B
        df[f"{k}_cont_b"] = sh / (tb + eps)          # share of B's word weight found in A
        df[f"{k}_jacc"] = sh / (ta + tb - sh + eps)  # weighted Jaccard
    df["name_len_ratio"] = np.minimum(df["a_name_len"], df["b_name_len"]) / (np.maximum(df["a_name_len"], df["b_name_len"]) + eps)
    df["n_words_diff"] = (df["a_n_words"] - df["b_n_words"]).abs()
    df["b_is_s3"] = (df["b_src"] == 3).astype(np.int8)
    for c in ("b_name_nonascii", "b_addr_nonascii", "b_addr_missing"):
        df[c] = df[c].astype(np.int8)
    return df


DROP = ["a_name_norm", "b_name_norm", "a_core", "b_core", "a_alt", "b_alt", "a_phon", "b_phon",
        "a_addr", "b_addr", "a_aw_s", "b_aw_s", "b_src", "a_name_len", "b_name_len"]


def feature_columns(df: pd.DataFrame) -> list[str]:
    skip = {"s1", "t", "label"}
    return [c for c in df.columns if c not in skip]


def main(split: str, top_k: int, frac: float) -> None:
    t0 = time.time()
    out_dir = FEAT / split
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("part-*.parquet"):
        old.unlink()
    con = connect(split)
    build_records(con, split)
    print(f"records + IDF {time.time() - t0:.0f}s", flush=True)
    n_chunks = build_context(con, split, top_k, frac)
    n = con.execute("SELECT count(*) FROM pairs").fetchone()[0]
    print(f"pairs {n:,}  {time.time() - t0:.0f}s", flush=True)
    import json
    (out_dir / "_meta.json").write_text(json.dumps({"top_k": top_k, "sample_per_mille": int(frac * 1000) if frac < 1 else 1000}))
    for ch in range(n_chunks):
        t = time.time()
        con.execute(f"CREATE OR REPLACE TEMP TABLE pc AS SELECT * FROM pairs WHERE chunk = {ch}")
        for col in ("nw", "pw", "aw"):
            con.execute(SQL_SHARED.format(col=col))
        df = con.execute(SQL_CHUNK).fetchdf()
        df = derived(string_features(df)).drop(columns=DROP)
        num = df.select_dtypes(include=["float64"]).columns
        df[num] = df[num].astype(np.float32)
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out_dir / f"part-{ch:02d}.parquet", compression="zstd")
        print(f"  chunk {ch + 1:2d}/{n_chunks}: {len(df):,} pairs  {time.time() - t:5.1f}s", flush=True)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30, float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
