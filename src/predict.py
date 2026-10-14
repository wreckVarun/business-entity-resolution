"""Score the test candidates and write the two submission files.

Input : data/features/test/part-*.parquet, models/lgbm_matcher.txt, models/decision.json
Output: output/matching_results.tsv   one row per test Source 1 entity, matched S2/S3 ids
        output/candidate_pairs.tsv    the exact candidate set the model scored

Usage: python src/predict.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEAT = ROOT / "data" / "features" / "test"
OUT = ROOT / "output"


def main() -> None:
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    decision = json.loads((ROOT / "models" / "decision.json").read_text())
    feats, t_top, t_more = decision["features"], decision["t_top"], decision["t_more"]
    model = lgb.Booster(model_file=str(ROOT / "models" / "lgbm_matcher.txt"))

    parts = []
    for f in sorted(FEAT.glob("part-*.parquet")):
        df = pd.read_parquet(f, columns=["s1", "t"] + feats)
        df["p"] = model.predict(df[feats].to_numpy(np.float32))
        parts.append(df[["s1", "t", "p"]])
    scored = pd.concat(parts, ignore_index=True)
    print(f"scored {len(scored):,} test pairs  ({time.time() - t0:.0f}s)")

    con = duckdb.connect()
    con.execute("SET threads=10")
    con.register("scored", scored)
    test_s1 = ROOT / "data" / "parquet" / "test_s1.parquet"
    con.execute(f"""
        CREATE TABLE ids AS
        SELECT entity_id, (CAST(substr(entity_id, 2, 1) AS BIGINT) * 10000000000 + CAST(substr(entity_id, 4) AS BIGINT)) eid
        FROM read_parquet(['{test_s1}', '{ROOT / 'data' / 'parquet' / 'test_s2.parquet'}', '{ROOT / 'data' / 'parquet' / 'test_s3.parquet'}'])
    """)
    # decision rule: each target is kept only for its most likely Source 1 entity; then a Source 1
    # entity's best remaining candidate is a match if p >= t_top, any further candidate if p >= t_more
    con.execute(f"""
        CREATE TABLE matches AS
        WITH excl AS (
            SELECT s1, t, p FROM scored
            QUALIFY row_number() OVER (PARTITION BY t ORDER BY p DESC, s1) = 1
        ), ranked AS (
            SELECT *, row_number() OVER (PARTITION BY s1 ORDER BY p DESC, t) r FROM excl
        )
        SELECT s1, t FROM ranked WHERE (r = 1 AND p >= {t_top}) OR (r > 1 AND p >= {t_more})
    """)
    for name, table, col in (("matching_results.tsv", "matches", "matched_entity_ids"),
                             ("candidate_pairs.tsv", "scored", "candidate_entity_ids")):
        con.execute(f"""
            COPY (
                SELECT s.entity_id AS source1_entity_id,
                       coalesce(string_agg(i.entity_id, ',' ORDER BY i.entity_id), '') AS {col}
                FROM '{test_s1}' s
                LEFT JOIN ids e1 ON e1.entity_id = s.entity_id
                LEFT JOIN {table} m ON m.s1 = e1.eid
                LEFT JOIN ids i ON i.eid = m.t
                GROUP BY s.entity_id
                ORDER BY s.entity_id
            ) TO '{OUT / name}' (HEADER, DELIMITER '\t', QUOTE '', ESCAPE '')
        """)
    n_s1, n_matched, n_links = con.execute(
        "SELECT (SELECT count(*) FROM ids WHERE entity_id LIKE 'S1-%'), count(DISTINCT s1), count(*) FROM matches").fetchone()
    print(f"{n_s1:,} test Source 1 entities, {n_matched:,} with at least one match, {n_links:,} links  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
