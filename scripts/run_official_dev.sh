#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
MODELS="${MWB_MODELS:-default}"
SEEDS="${SEEDS:-1337,2026,9001}"
MAX_TURNS="${MAX_TURNS:-4}"
MODEL_TIMEOUT_SECONDS="${MODEL_TIMEOUT_SECONDS:-${TIMEOUT_SECONDS:-180}}"
TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS:-8}"
MODEL_RETRIES="${MODEL_RETRIES:-1}"
MODEL_RETRY_BACKOFF_SECONDS="${MODEL_RETRY_BACKOFF_SECONDS:-1.0}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-640}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-220}"
RESULTS_PATH="${RESULTS_PATH:-results/official_dev_protocol-${PROTOCOL_VERSION}_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/official_dev_protocol-${PROTOCOL_VERSION}_run.log}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SEEDS_TOKEN="${SEEDS//,/-}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/official_dev_protocol-${PROTOCOL_VERSION}_seeds-${SEEDS_TOKEN}_${STAMP}.zip}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack task_pack_v2 --suite dev --models ${MODELS} --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise --repro --max-turns ${MAX_TURNS} --model-timeout ${MODEL_TIMEOUT_SECONDS} --test-timeout ${TEST_TIMEOUT_SECONDS} --model-retries ${MODEL_RETRIES} --model-retry-backoff ${MODEL_RETRY_BACKOFF_SECONDS} --worker-num-predict ${WORKER_NUM_PREDICT} --mentor-num-predict ${MENTOR_NUM_PREDICT} --seeds ${SEEDS} --results-path ${RESULTS_PATH}"

echo "Running official dev headline suite with seeds ${SEEDS}..."
echo "Note: this is the full headline publication path and is not a realistic default local gate on a 16 GB MacBook Air. Use ./scripts/run_local_verification.sh for local release-health checks."
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite dev \
  --models "${MODELS}" \
  --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise \
  --repro \
  --max-turns "${MAX_TURNS}" \
  --model-timeout "${MODEL_TIMEOUT_SECONDS}" \
  --test-timeout "${TEST_TIMEOUT_SECONDS}" \
  --model-retries "${MODEL_RETRIES}" \
  --model-retry-backoff "${MODEL_RETRY_BACKOFF_SECONDS}" \
  --worker-num-predict "${WORKER_NUM_PREDICT}" \
  --mentor-num-predict "${MENTOR_NUM_PREDICT}" \
  --seeds "${SEEDS}" \
  --results-path "${RESULTS_PATH}" 2>&1 | tee "${RUN_LOG_PATH}"; then
  echo "Official dev run failed. Last 30 log lines:" >&2
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
echo "- Run log: ${RUN_LOG_PATH}"
echo "- Submission: ${SUBMISSION_PATH}"
