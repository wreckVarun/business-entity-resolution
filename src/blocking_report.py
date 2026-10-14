"""How good is the candidate set? Recall and pair counts for different top-K cut-offs.

  pair recall      share of true (S1, S2/S3) pairs that survive blocking
  ceiling F0.5     the entity F0.5 a perfect classifier would get on these candidates
                   (blocking misses are the only errors)
  reduction ratio  1 - candidates / all same-country pairs

Usage: python src/blocking_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
PQ = ROOT / "data" / "parquet"


def eid(col: str) -> str:
    return f"(CAST(substr({col}, 2, 1) AS BIGINT) * 10000000000 + CAST(substr({col}, 4) AS BIGINT))"


def main() -> None:
    con = duckdb.connect()
    con.execute(f"SET threads=10; SET memory_limit='10GB'; SET temp_directory='{WORK / 'tmp'}'")
    con.execute(f"""CREATE TABLE gt AS SELECT {eid('source1_entity_id')} s1, {eid('m')} t FROM (
        SELECT source1_entity_id, unnest(string_split(matched_entity_ids, ',')) m FROM '{PQ / 'train_gt.parquet'}'
        WHERE matched_entity_ids IS NOT NULL AND matched_entity_ids <> '')""")
    con.execute(f"CREATE TABLE gtn AS SELECT {eid('source1_entity_id')} s1, CASE WHEN matched_entity_ids IS NULL OR matched_entity_ids = '' THEN 0 ELSE len(string_split(matched_entity_ids, ',')) END n_true FROM '{PQ / 'train_gt.parquet'}'")
    con.execute(f"CREATE TABLE c AS SELECT s1, t, rnk FROM '{WORK / 'train_cands.parquet'}'")
    con.execute("CREATE TABLE hit AS SELECT c.s1, c.t, c.rnk FROM c JOIN gt USING (s1, t)")
    n_true = con.execute("SELECT count(*) FROM gt").fetchone()[0]
    n_s1 = con.execute("SELECT count(*) FROM gtn").fetchone()[0]
    all_pairs = con.execute(f"""SELECT sum(a.n * b.n) FROM
        (SELECT country, count(*) n FROM '{PQ / 'train_s1.parquet'}' GROUP BY 1) a JOIN
        (SELECT country, count(*) n FROM read_parquet(['{PQ / 'train_s2.parquet'}', '{PQ / 'train_s3.parquet'}']) GROUP BY 1) b USING (country)""").fetchone()[0]
    rows = []
    for k in (1, 3, 5, 10, 15, 20, 30, 40, 50, 75, 100):
        n_c, = con.execute(f"SELECT count(*) FROM c WHERE rnk <= {k}").fetchone()
        n_h, = con.execute(f"SELECT count(*) FROM hit WHERE rnk <= {k}").fetchone()
        # perfect classifier on the top-k: precision 1, recall = found / true per entity
        ceiling, = con.execute(f"""
            SELECT avg(CASE WHEN g.n_true = 0 THEN 1.0
                            WHEN coalesce(h.found, 0) = 0 THEN 0.0
                            ELSE 1.25 * (h.found * 1.0 / g.n_true) / (0.25 + h.found * 1.0 / g.n_true) END)
            FROM gtn g LEFT JOIN (SELECT s1, count(*) found FROM hit WHERE rnk <= {k} GROUP BY 1) h USING (s1)""").fetchone()
        rows.append({"top_k": k, "pairs": n_c, "pairs_per_s1": round(n_c / n_s1, 2),
                     "pair_recall": round(n_h / n_true, 4), "ceiling_f05": round(ceiling, 4),
                     "reduction_ratio": round(1 - n_c / all_pairs, 8)})
        print(rows[-1], flush=True)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "blocking.json").write_text(json.dumps({"all_same_country_pairs": all_pairs, "true_pairs": n_true, "by_top_k": rows}, indent=2))


if __name__ == "__main__":
    main()
