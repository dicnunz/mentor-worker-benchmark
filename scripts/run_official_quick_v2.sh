#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
WORKER_MODELS="${WORKER_MODELS:-qwen2.5-coder:7b,phi3:mini}"
MENTOR_MODELS="${MENTOR_MODELS:-llama3.1:8b}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker}"
MAX_TURNS="${MAX_TURNS:-2}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-20}"
SEED="${SEED:-1337}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-220}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-120}"
RESULTS_PATH="${RESULTS_PATH:-results/official_quick_v2_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_quick_v2_run.log}"
STAMP="$(date +%F)"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_quick_v2_m3air_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite quick --mentor-models ${MENTOR_MODELS} --worker-models ${WORKER_MODELS} --run-modes ${RUN_MODES} --max-turns ${MAX_TURNS} --timeout ${TIMEOUT_SECONDS} --seed ${SEED} --worker-num-predict ${WORKER_NUM_PREDICT} --mentor-num-predict ${MENTOR_NUM_PREDICT} --results-path ${RESULTS_PATH}"

echo "Running official quick v2 suite..."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite quick \
  --mentor-models "${MENTOR_MODELS}" \
  --worker-models "${WORKER_MODELS}" \
  --run-modes "${RUN_MODES}" \
  --max-turns "${MAX_TURNS}" \
  --timeout "${TIMEOUT_SECONDS}" \
  --seed "${SEED}" \
  --worker-num-predict "${WORKER_NUM_PREDICT}" \
  --mentor-num-predict "${MENTOR_NUM_PREDICT}" \
  --results-path "${RESULTS_PATH}" 2>&1 | tee "${RUN_LOG_PATH}"; then
  echo "Official quick v2 run failed. Last 30 log lines:" >&2
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
