"""Check both output files against the submission rules in the problem statement.

Rules checked:
  - tab-separated with the exact header
  - exactly one row per test Source 1 entity, no extra or duplicate rows
  - ID lists contain only S2-/S3- ids that exist in the test set, no duplicates within a list
  - every matched id also appears in that entity's candidate list

Usage: python src/validate_submission.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_ids(path: Path) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r)
        return {row[0] for row in r}


def read_output(path: Path, header: list[str], problems: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        got = next(r)
        if got != header:
            problems.append(f"{path.name}: header {got} != {header}")
        for i, row in enumerate(r, start=2):
            if len(row) not in (1, 2):
                problems.append(f"{path.name}:{i}: expected 2 columns, got {len(row)}")
                continue
            s1, ids = row[0], (row[1] if len(row) == 2 else "")
            if s1 in rows:
                problems.append(f"{path.name}:{i}: duplicate row for {s1}")
            lst = [x for x in ids.split(",") if x] if ids else []
            if len(lst) != len(set(lst)):
                problems.append(f"{path.name}:{i}: duplicate ids in list for {s1}")
            rows[s1] = lst
    return rows


def main() -> int:
    test = ROOT / "data" / "raw" / "test"
    s1 = read_ids(test / "test_source1.tsv")
    targets = read_ids(test / "test_source2.tsv") | read_ids(test / "test_source3.tsv")
    problems: list[str] = []
    match = read_output(ROOT / "output" / "matching_results.tsv", ["source1_entity_id", "matched_entity_ids"], problems)
    cand = read_output(ROOT / "output" / "candidate_pairs.tsv", ["source1_entity_id", "candidate_entity_ids"], problems)
    for name, rows in (("matching_results", match), ("candidate_pairs", cand)):
        missing, extra = s1 - rows.keys(), rows.keys() - s1
        if missing:
            problems.append(f"{name}: {len(missing):,} test Source 1 entities have no row")
        if extra:
            problems.append(f"{name}: {len(extra):,} rows are not test Source 1 entities")
        bad = sum(1 for lst in rows.values() for x in lst if x not in targets)
        if bad:
            problems.append(f"{name}: {bad:,} ids are not Source 2/3 ids of the test set")
    not_cand = sum(1 for k, lst in match.items() for x in lst if x not in set(cand.get(k, [])))
    if not_cand:
        problems.append(f"{not_cand:,} matched ids were never candidates (pipeline bug)")
    if problems:
        print("FAIL")
        for i, p in enumerate(problems[:50], 1):
            print(f"{i}. {p}")
        return 1
    n_links = sum(len(v) for v in match.values())
    print(f"PASS  {len(match):,} entities, {n_links:,} matched ids, "
          f"{sum(1 for v in match.values() if not v):,} predicted singletons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
