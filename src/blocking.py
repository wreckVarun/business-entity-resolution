"""Candidate generation (blocking).

Comparing every Source 1 record with every Source 2/3 record in the same
country would mean ~8 trillion pairs on the training data. Instead, each
record gets a set of blocking keys, and two records become a candidate pair
only if they share at least one key that is rare enough.

Key families (all within the same country):
    nc   cleaned name word                     ('montari')
    np   phonetic name word                     ('mntr'), for transliterated names
    ab   address word pair                      ('tanglewood pass')
    nca  name word + address word               ('montari#tanglewood')
    npa  phonetic name word + address word
    nf   whole cleaned name                     ('montari spire')
    pf   whole phonetic name
    ns   cleaned name without spaces            ('indiancare'), catches joined words
    nh   name word + house number               ('zasoft#290')
    ah   address word + house number            ('tanglewood#34184')

A key is only used if at most CAP[kind] target records carry it; more common
keys (city names, 'service', ...) would create huge numbers of useless pairs.
Each candidate pair is scored by the summed IDF of the keys it shares, and
only the TOP_K best-scoring targets are kept per Source 1 record.

Usage: python src/blocking.py train|test [top_k]
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
NORM = ROOT / "data" / "norm"
WORK = ROOT / "data" / "work"

CAP = {"nc": 200, "np": 200, "ab": 200, "nca": 200, "npa": 200,
       "nf": 1000, "pf": 1000, "ns": 1000, "nh": 200, "ah": 200}
KINDS = list(CAP)
PARTS = 64
TOP_K = 50


def eid(col: str = "entity_id") -> str:
    """S2-681193310 -> 20681193310 (source digit in front of the number), as BIGINT."""
    return f"(CAST(substr({col}, 2, 1) AS BIGINT) * 10000000000 + CAST(substr({col}, 4) AS BIGINT))"


def connect(split: str) -> duckdb.DuckDBPyConnection:
    WORK.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WORK / f"{split}_blocking.duckdb"))
    threads, mem = os.environ.get("ER_THREADS", "10"), os.environ.get("ER_MEMORY", "11GB")
    con.execute(f"SET threads={threads}; SET memory_limit='{mem}'; SET temp_directory='{WORK / 'tmp'}'; "
                "SET preserve_insertion_order=false")
    return con


def build_keys(con, split: str) -> None:
    files = [str(NORM / f"{split}_s{i}.parquet") for i in (1, 2, 3)]
    con.execute(f"""CREATE OR REPLACE TABLE rec AS
        SELECT {eid()} eid, country, src, name_core, coalesce(name_alt, '') name_alt, name_phon,
               addr_words, house_no
        FROM read_parquet({files})""")
    # word lists per record
    con.execute("""CREATE OR REPLACE TEMP TABLE words AS SELECT eid, country, src, house_no, name_core, name_phon,
        list_distinct(list_filter(string_split(name_core || ' ' || replace(name_alt, '|', ' '), ' '), lambda x: length(x) > 1)) nw,
        list_distinct(list_filter(string_split(name_phon, ' '), lambda x: length(x) > 1)) pw,
        list_distinct(list_filter(string_split(addr_words, ' '), lambda x: length(x) > 2)) aw,
        string_split(addr_words, ' ') a_all
        FROM rec""")
    con.execute("""CREATE OR REPLACE TABLE keys AS
        WITH nw AS (SELECT eid, country, src, house_no, unnest(nw) w FROM words),
             pw AS (SELECT eid, country, src, unnest(pw) w FROM words),
             aw AS (SELECT eid, country, src, house_no, unnest(aw) w FROM words)
        SELECT eid, country, src, 'nc' kind, hash(w) k FROM nw
        UNION ALL SELECT eid, country, src, 'np', hash(w) FROM pw
        UNION ALL SELECT eid, country, src, 'ab', unnest(list_distinct(list_transform(range(1, len(a_all)),
                         lambda i: hash(a_all[i] || ' ' || a_all[i + 1])))) FROM words WHERE len(a_all) > 1
        UNION ALL SELECT n.eid, n.country, n.src, 'nca', hash(n.w || '#' || a.w) FROM nw n JOIN aw a USING (eid)
        UNION ALL SELECT p.eid, p.country, p.src, 'npa', hash(p.w || '#' || a.w) FROM pw p JOIN aw a USING (eid)
        UNION ALL SELECT eid, country, src, 'nf', hash(name_core) FROM words WHERE name_core <> ''
        UNION ALL SELECT eid, country, src, 'pf', hash(name_phon) FROM words WHERE name_phon <> ''
        UNION ALL SELECT eid, country, src, 'ns', hash(replace(name_core, ' ', '')) FROM words WHERE name_core <> ''
        UNION ALL SELECT eid, country, src, 'nh', hash(w || '#' || house_no) FROM nw WHERE house_no <> ''
        UNION ALL SELECT eid, country, src, 'ah', hash(w || '#' || house_no) FROM aw WHERE house_no <> ''
    """)
    caps = " OR ".join(f"(kind = '{k}' AND df_t <= {c})" for k, c in CAP.items())
    con.execute(f"""CREATE OR REPLACE TABLE kdf AS
        SELECT country, kind, k, count(*) FILTER (WHERE src > 1) df_t, count(*) FILTER (WHERE src = 1) df_1
        FROM keys GROUP BY ALL""")
    # keep only usable keys: present on both sides and rare enough on the target side
    con.execute(f"""CREATE OR REPLACE TABLE kdf_use AS
        SELECT d.country, d.kind, d.k, d.df_t,
               ln((n.n_t + 1.0) / (d.df_t + 1.0)) idf
        FROM kdf d JOIN (SELECT country, count(*) FILTER (WHERE src > 1) n_t FROM rec GROUP BY 1) n USING (country)
        WHERE d.df_1 > 0 AND d.df_t > 0 AND ({caps})""")
    con.execute("""CREATE OR REPLACE TABLE k1 AS SELECT k.eid s1, k.country, k.kind, k.k, u.idf
                   FROM keys k JOIN kdf_use u USING (country, kind, k) WHERE k.src = 1""")
    con.execute("""CREATE OR REPLACE TABLE kt AS SELECT k.eid t, k.country, k.kind, k.k
                   FROM keys k SEMI JOIN kdf_use u USING (country, kind, k) WHERE k.src > 1""")
    con.execute("DROP TABLE keys")


def generate(con, top_k: int) -> None:
    # which key families matched, as a bitmask (bit i = KINDS[i]); keeps the aggregation narrow
    bit = "CASE kind " + " ".join(f"WHEN '{k}' THEN {1 << i}" for i, k in enumerate(KINDS)) + " END"
    con.execute(f"SET threads={min(8, int(os.environ.get('ER_THREADS', '8')))}")
    con.execute("DROP TABLE IF EXISTS cands")
    con.execute("""CREATE TABLE cands (s1 BIGINT, t BIGINT, score DOUBLE, n_keys INTEGER, kinds USMALLINT, rnk INTEGER)""")
    for p in range(PARTS):
        t = time.time()
        con.execute(f"""
            INSERT INTO cands
            WITH hits AS (
                SELECT a.s1, b.t, a.idf, {bit} AS kb
                FROM (SELECT * FROM k1 WHERE hash(s1) % {PARTS} = {p}) a
                JOIN kt b USING (country, kind, k)
            ),
            agg AS (SELECT s1, t, sum(idf) score, count(*)::INTEGER n_keys, bit_or(kb)::USMALLINT kinds
                    FROM hits GROUP BY s1, t)
            SELECT s1, t, score, n_keys, kinds,
                   row_number() OVER (PARTITION BY s1 ORDER BY score DESC, t)::INTEGER AS rnk
            FROM agg QUALIFY rnk <= {top_k}
        """)
        if p % 8 == 7 or p == 0:
            print(f"  part {p + 1:2d}/{PARTS}  {time.time() - t:5.1f}s", flush=True)


def main(split: str, top_k: int) -> None:
    t = time.time()
    con = connect(split)
    if "--reuse-keys" not in sys.argv:
        build_keys(con, split)
    print(f"keys built {time.time() - t:.0f}s", con.execute("SELECT kind, count(*) FROM k1 GROUP BY 1 ORDER BY 1").fetchall())
    generate(con, top_k)
    out = WORK / f"{split}_cands.parquet"
    con.execute(f"COPY cands TO '{out}' (FORMAT parquet, COMPRESSION zstd)")
    n, s1 = con.execute("SELECT count(*), count(DISTINCT s1) FROM cands").fetchone()
    print(f"{split}: {n:,} candidate pairs for {s1:,} Source 1 records -> {out}  ({time.time() - t:.0f}s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], int(args[1]) if len(args) > 1 else TOP_K)
