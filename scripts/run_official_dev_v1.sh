#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
TASK_PACK="${TASK_PACK:-task_pack_v2}"
TASK_SUITE="${TASK_SUITE:-dev50}"
WORKER_MODELS="${WORKER_MODELS:-qwen2.5-coder:7b}"
MENTOR_MODELS="${MENTOR_MODELS:-llama3.1:8b,mistral:7b}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker,mentor_only_suggestion_noise}"
MAX_TURNS="${MAX_TURNS:-2}"
MODEL_TIMEOUT_SECONDS="${MODEL_TIMEOUT_SECONDS:-${TIMEOUT_SECONDS:-20}}"
TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS:-8}"
MODEL_RETRIES="${MODEL_RETRIES:-1}"
MODEL_RETRY_BACKOFF_SECONDS="${MODEL_RETRY_BACKOFF_SECONDS:-1.0}"
SEEDS="${SEEDS:-1337,2026,9001}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-220}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-120}"
RESULTS_PATH="${RESULTS_PATH:-results/official_${TASK_SUITE}_protocol-${PROTOCOL_VERSION}_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_${TASK_SUITE}_protocol-${PROTOCOL_VERSION}_run.log}"
STAMP="$(date +%F)"
SEEDS_TOKEN="${SEEDS//,/-}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_${TASK_SUITE}_protocol-${PROTOCOL_VERSION}_seeds-${SEEDS_TOKEN}_m3air_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ "${TASK_SUITE}" != "dev" && "${TASK_SUITE}" != "dev50" && "${TASK_SUITE}" != "test" ]]; then
  echo "TASK_SUITE must be dev, dev50, or test (got ${TASK_SUITE})" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack ${TASK_PACK} --suite ${TASK_SUITE} --mentor-models ${MENTOR_MODELS} --worker-models ${WORKER_MODELS} --run-modes ${RUN_MODES} --max-turns ${MAX_TURNS} --model-timeout ${MODEL_TIMEOUT_SECONDS} --test-timeout ${TEST_TIMEOUT_SECONDS} --model-retries ${MODEL_RETRIES} --model-retry-backoff ${MODEL_RETRY_BACKOFF_SECONDS} --seeds ${SEEDS} --worker-num-predict ${WORKER_NUM_PREDICT} --mentor-num-predict ${MENTOR_NUM_PREDICT} --results-path ${RESULTS_PATH}"

echo "Running official protocol suite (${TASK_SUITE}) with seeds ${SEEDS}..."
echo "Note: this is a headline/publication script and is not the practical default local gate on a 16 GB MacBook Air. Use ./scripts/run_local_verification.sh for local release-health checks."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack "${TASK_PACK}" \
  --suite "${TASK_SUITE}" \
  --mentor-models "${MENTOR_MODELS}" \
  --worker-models "${WORKER_MODELS}" \
  --run-modes "${RUN_MODES}" \
  --max-turns "${MAX_TURNS}" \
  --model-timeout "${MODEL_TIMEOUT_SECONDS}" \
  --test-timeout "${TEST_TIMEOUT_SECONDS}" \
  --model-retries "${MODEL_RETRIES}" \
  --model-retry-backoff "${MODEL_RETRY_BACKOFF_SECONDS}" \
  --seeds "${SEEDS}" \
  --worker-num-predict "${WORKER_NUM_PREDICT}" \
  --mentor-num-predict "${MENTOR_NUM_PREDICT}" \
  --results-path "${RESULTS_PATH}" 2>&1 | tee "${RUN_LOG_PATH}"; then
  echo "Official protocol run failed. Last 30 log lines:" >&2
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
