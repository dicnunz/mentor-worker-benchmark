#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
WORKER_MODELS="${WORKER_MODELS:-qwen2.5-coder:7b,phi3:mini}"
MENTOR_MODELS="${MENTOR_MODELS:-llama3.1:8b}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker}"
MAX_TURNS="${MAX_TURNS:-3}"
MODEL_TIMEOUT_SECONDS="${MODEL_TIMEOUT_SECONDS:-${TIMEOUT_SECONDS:-180}}"
TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS:-8}"
MODEL_RETRIES="${MODEL_RETRIES:-1}"
MODEL_RETRY_BACKOFF_SECONDS="${MODEL_RETRY_BACKOFF_SECONDS:-1.0}"
SEEDS="${SEEDS:-1337}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-512}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-256}"
RESULTS_PATH="${RESULTS_PATH:-results/official_quick_v2_protocol-${PROTOCOL_VERSION}_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_quick_v2_protocol-${PROTOCOL_VERSION}_run.log}"
STAMP="$(date +%F)"
SEEDS_TOKEN="${SEEDS//,/-}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_quick_v2_protocol-${PROTOCOL_VERSION}_seeds-${SEEDS_TOKEN}_m3air_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite quick --mentor-models ${MENTOR_MODELS} --worker-models ${WORKER_MODELS} --run-modes ${RUN_MODES} --repro --max-turns ${MAX_TURNS} --model-timeout ${MODEL_TIMEOUT_SECONDS} --test-timeout ${TEST_TIMEOUT_SECONDS} --model-retries ${MODEL_RETRIES} --model-retry-backoff ${MODEL_RETRY_BACKOFF_SECONDS} --seeds ${SEEDS} --worker-num-predict ${WORKER_NUM_PREDICT} --mentor-num-predict ${MENTOR_NUM_PREDICT} --results-path ${RESULTS_PATH}"

echo "Running official quick v2 suite with seeds ${SEEDS}..."
echo "Note: this script produces an official sanity artifact. For practical local release-health verification on a 16 GB MacBook Air, use ./scripts/run_local_verification.sh first."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite quick \
  --mentor-models "${MENTOR_MODELS}" \
  --worker-models "${WORKER_MODELS}" \
  --run-modes "${RUN_MODES}" \
  --repro \
  --max-turns "${MAX_TURNS}" \
  --model-timeout "${MODEL_TIMEOUT_SECONDS}" \
  --test-timeout "${TEST_TIMEOUT_SECONDS}" \
  --model-retries "${MODEL_RETRIES}" \
  --model-retry-backoff "${MODEL_RETRY_BACKOFF_SECONDS}" \
  --seeds "${SEEDS}" \
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
