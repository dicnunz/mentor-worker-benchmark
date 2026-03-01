#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
WORKER_MODEL="${WORKER_MODEL:-phi3:mini}"
MENTOR_MODEL="${MENTOR_MODEL:-llama3.1:8b}"
RESULTS_PATH="${RESULTS_PATH:-results/official_quick_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_quick_run.log}"
STAMP="$(date +%F)"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_quick_m3air_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite quick --mentor-models ${MENTOR_MODEL} --worker-models ${WORKER_MODEL} --run-modes worker_only --max-turns 1 --timeout 8 --seed 1337 --results-path ${RESULTS_PATH}"

echo "Running official quick suite..."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite quick \
  --mentor-models "${MENTOR_MODEL}" \
  --worker-models "${WORKER_MODEL}" \
  --run-modes worker_only \
  --max-turns 1 \
  --timeout 8 \
  --seed 1337 \
  --results-path "${RESULTS_PATH}" 2>&1 | tee "${RUN_LOG_PATH}"; then
  echo "Official quick run failed. Last 30 log lines:" >&2
  tail -n 30 "${RUN_LOG_PATH}" >&2 || true
  exit 1
fi

echo "Exporting submission bundle..."
"${PYTHON_BIN}" -m mentor_worker_benchmark export \
  --results "${RESULTS_PATH}" \
  --out "${SUBMISSION_PATH}" \
  --official \
  --command "${RUN_COMMAND}"

echo "Verifying submission bundle..."
"${PYTHON_BIN}" -m mentor_worker_benchmark verify --submission "${SUBMISSION_PATH}"

echo "Done."
echo "- Results: ${RESULTS_PATH}"
echo "- Submission ZIP: ${SUBMISSION_PATH}"
