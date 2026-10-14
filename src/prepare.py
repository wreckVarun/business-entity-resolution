"""Normalise every source file once and store the result as Parquet.

Input : data/parquet/{split}_s{1,2,3}.parquet   (from load.py)
Output: data/norm/{split}_s{1,2,3}.parquet

Runs in parallel over chunks of rows (one process per CPU core).
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize_record  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "parquet"
OUT = ROOT / "data" / "norm"
CHUNK = 200_000

FIELDS = ["name_norm", "name_core", "name_alt", "name_phon", "addr_norm", "addr_words", "addr_nums", "house_no"]


def _work(batch: dict) -> pa.Table:
    names, addrs = batch["business_name"], batch["business_address"]
    cols = {f: [] for f in FIELDS}
    name_nonascii, addr_nonascii, addr_missing = [], [], []
    for n, a in zip(names, addrs):
        n = n or ""
        a = "" if a is None or a.strip().lower() in ("", "none", "null", "nan") else a
        rec = normalize_record(n, a)
        for f in FIELDS:
            cols[f].append(rec[f])
        name_nonascii.append(not n.isascii())
        addr_nonascii.append(not a.isascii())
        addr_missing.append(a == "")
    return pa.table({
        "entity_id": batch["entity_id"],
        "country": batch["country"],
        "business_name": names,
        "business_address": addrs,
        **cols,
        "name_nonascii": name_nonascii,
        "addr_nonascii": addr_nonascii,
        "addr_missing": addr_missing,
    })


def run(name: str, pool: Pool) -> None:
    t = time.time()
    table = pq.read_table(SRC / f"{name}.parquet")
    batches = [table.slice(i, CHUNK).to_pydict() for i in range(0, table.num_rows, CHUNK)]
    parts = pool.map(_work, batches)
    out = pa.concat_tables(parts)
    src = int(name[-1])
    out = out.append_column("src", pa.array([src] * out.num_rows, pa.int8()))
    pq.write_table(out, OUT / f"{name}.parquet", compression="zstd")
    print(f"{name:9s} {out.num_rows:>10,} rows  {time.time() - t:6.1f}s", flush=True)


def main(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with Pool(os.cpu_count()) as pool:
        for name in names:
            run(name, pool)


if __name__ == "__main__":
    main(sys.argv[1:] or ["train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"])
