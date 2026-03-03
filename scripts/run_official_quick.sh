#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
WORKER_MODELS="${WORKER_MODELS:-phi3:mini,qwen2.5-coder:7b}"
MENTOR_MODELS="${MENTOR_MODELS:-llama3.1:8b,mistral:7b}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker}"
SEEDS="${SEEDS:-1337}"
RESULTS_PATH="${RESULTS_PATH:-results/official_quick_protocol-${PROTOCOL_VERSION}_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_quick_protocol-${PROTOCOL_VERSION}_run.log}"
STAMP="$(date +%F)"
SEEDS_TOKEN="${SEEDS//,/-}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_quick_protocol-${PROTOCOL_VERSION}_seeds-${SEEDS_TOKEN}_m3air_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite quick --mentor-models ${MENTOR_MODELS} --worker-models ${WORKER_MODELS} --run-modes ${RUN_MODES} --max-turns 1 --timeout 8 --seeds ${SEEDS} --results-path ${RESULTS_PATH}"

echo "Running official quick suite with seeds ${SEEDS}..."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite quick \
  --mentor-models "${MENTOR_MODELS}" \
  --worker-models "${WORKER_MODELS}" \
  --run-modes "${RUN_MODES}" \
  --max-turns 1 \
  --timeout 8 \
  --seeds "${SEEDS}" \
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
