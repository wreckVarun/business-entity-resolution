"""Convert the raw challenge TSVs to Parquet.

The TSVs are read with quoting disabled: the files are tab-separated with no
quoting, and names/addresses can contain stray quote characters that would
otherwise swallow the rest of the file.

Usage: python src/load.py
"""
from __future__ import annotations

import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "parquet"

FILES = {
    "train_s1": "train/train_source1.tsv",
    "train_s2": "train/train_source2.tsv",
    "train_s3": "train/train_source3.tsv",
    "train_gt": "train/train_ground_truth.tsv",
    "test_s1": "test/test_source1.tsv",
    "test_s2": "test/test_source2.tsv",
    "test_s3": "test/test_source3.tsv",
}


def find(rel: str) -> Path:
    hits = sorted(RAW.rglob(Path(rel).name))
    if not hits:
        raise FileNotFoundError(f"{rel} not found under {RAW}")
    return hits[0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for name, rel in FILES.items():
        t = time.time()
        src = find(rel)
        dst = OUT / f"{name}.parquet"
        con.execute(
            f"""
            COPY (
                SELECT * FROM read_csv('{src}', delim='\t', header=true, quote='', escape='',
                                       all_varchar=true, null_padding=true, strict_mode=false)
            ) TO '{dst}' (FORMAT parquet, COMPRESSION zstd)
            """
        )
        n, cols = con.execute(f"SELECT count(*), (SELECT list(column_name) FROM (DESCRIBE SELECT * FROM '{dst}')) FROM '{dst}'").fetchone()
        print(f"{name:9s} {n:>10,} rows  {cols}  ({time.time() - t:.1f}s)")


if __name__ == "__main__":
    main()
