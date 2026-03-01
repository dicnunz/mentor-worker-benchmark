#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
MODELS="${MWB_MODELS:-default}"
RESULTS_PATH="${RESULTS_PATH:-results/official_dev_results.json}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_dev_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite dev --models ${MODELS} --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise --repro --seed 1337 --results-path ${RESULTS_PATH}"

echo "Running official dev suite..."
"${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite dev \
  --models "${MODELS}" \
  --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise \
  --repro \
  --seed 1337 \
  --results-path "${RESULTS_PATH}"

echo "Exporting submission bundle..."
"${PYTHON_BIN}" -m mentor_worker_benchmark export \
  --results "${RESULTS_PATH}" \
  --out "${SUBMISSION_PATH}" \
  --command "${RUN_COMMAND}"

echo "Verifying submission bundle..."
"${PYTHON_BIN}" -m mentor_worker_benchmark verify --submission "${SUBMISSION_PATH}"

echo "Done."
echo "- Results: ${RESULTS_PATH}"
echo "- Submission: ${SUBMISSION_PATH}"
