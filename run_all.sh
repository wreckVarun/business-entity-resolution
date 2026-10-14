#!/usr/bin/env bash
# Full pipeline. Expects the challenge files under data/raw/{train,test}/.
# Peak memory is about 9 GB; DuckDB spills the rest to data/work/tmp.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python}

$PY src/load.py                      # TSV -> Parquet
$PY src/prepare.py                   # normalise names and addresses
$PY src/blocking.py train 100        # candidate pairs (top-100 kept for the recall report)
$PY src/blocking_report.py           # blocking recall by top-K
$PY src/features.py train 40 0.3     # pair features, 30% sample of training entities
$PY src/train.py                     # LightGBM + decision thresholds
$PY src/blocking.py test 40
$PY src/features.py test 40 1.0
$PY src/predict.py                   # output/matching_results.tsv, output/candidate_pairs.tsv
$PY src/validate_submission.py
$PY src/error_analysis.py
$PY src/figures.py
