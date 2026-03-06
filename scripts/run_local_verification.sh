#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
TASK_PACK="${TASK_PACK:-task_pack_v2}"
TASK_SUITE="${TASK_SUITE:-dev10}"
WORKER_MODEL="${WORKER_MODEL:-phi3:mini}"
MENTOR_MODEL="${MENTOR_MODEL:-phi3:mini}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker}"
SEED="${SEED:-1337}"
MAX_TURNS="${MAX_TURNS:-3}"
MODEL_TIMEOUT_SECONDS="${MODEL_TIMEOUT_SECONDS:-${TIMEOUT_SECONDS:-180}}"
TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS:-8}"
MODEL_RETRIES="${MODEL_RETRIES:-1}"
MODEL_RETRY_BACKOFF_SECONDS="${MODEL_RETRY_BACKOFF_SECONDS:-1.0}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-512}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-256}"
PREFLIGHT_TIMEOUT_SECONDS="${PREFLIGHT_TIMEOUT_SECONDS:-30}"
PREFLIGHT_ATTEMPTS="${PREFLIGHT_ATTEMPTS:-2}"
WORKER_MODEL_TOKEN="$(printf '%s' "${WORKER_MODEL}" | tr ':/' '__')"
MENTOR_MODEL_TOKEN="$(printf '%s' "${MENTOR_MODEL}" | tr ':/' '__')"
PREFLIGHT_MODELS="${WORKER_MODEL}"
if [[ "${MENTOR_MODEL}" != "${WORKER_MODEL}" ]]; then
  PREFLIGHT_MODELS="${WORKER_MODEL},${MENTOR_MODEL}"
fi
RESULTS_PATH="${RESULTS_PATH:-results/local_verification_${TASK_SUITE}_${WORKER_MODEL_TOKEN}_${MENTOR_MODEL_TOKEN}_protocol-${PROTOCOL_VERSION}_seed-${SEED}.json}"
PREFLIGHT_PATH="${PREFLIGHT_PATH:-results/local_verification_${TASK_SUITE}_${WORKER_MODEL_TOKEN}_${MENTOR_MODEL_TOKEN}_protocol-${PROTOCOL_VERSION}_seed-${SEED}_preflight.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/local_verification_${TASK_SUITE}_${WORKER_MODEL_TOKEN}_${MENTOR_MODEL_TOKEN}_protocol-${PROTOCOL_VERSION}_seed-${SEED}_run.log}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/local_verification_${TASK_SUITE}_${WORKER_MODEL_TOKEN}_${MENTOR_MODEL_TOKEN}_protocol-${PROTOCOL_VERSION}_seed-${SEED}.zip}"
RESULTS_STEM="${RESULTS_PATH%.*}"
CHECKPOINT_PATH="${RESULTS_STEM}.checkpoint.jsonl"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ "${TASK_SUITE}" != "quick" && "${TASK_SUITE}" != "dev10" ]]; then
  echo "TASK_SUITE must be quick or dev10 for local verification (got ${TASK_SUITE})." >&2
  exit 1
fi

mkdir -p "$(dirname "${RESULTS_PATH}")" "$(dirname "${SUBMISSION_PATH}")"

echo "Local verification profile:"
echo "- single-seed local release-health check"
echo "- not a headline publication run"
echo "- resumable via ${CHECKPOINT_PATH}"

echo "[1/5] Backend preflight"
"${PYTHON_BIN}" -m mentor_worker_benchmark preflight \
  --models "${PREFLIGHT_MODELS}" \
  --model-timeout "${PREFLIGHT_TIMEOUT_SECONDS}" \
  --attempts "${PREFLIGHT_ATTEMPTS}" \
  --seed "${SEED}" \
  --out "${PREFLIGHT_PATH}"

RUN_COMMAND="${PYTHON_BIN} -m mentor_worker_benchmark run --task-pack ${TASK_PACK} --suite ${TASK_SUITE} --mentor-model ${MENTOR_MODEL} --worker-model ${WORKER_MODEL} --run-modes ${RUN_MODES} --repro --max-turns ${MAX_TURNS} --model-timeout ${MODEL_TIMEOUT_SECONDS} --test-timeout ${TEST_TIMEOUT_SECONDS} --model-retries ${MODEL_RETRIES} --model-retry-backoff ${MODEL_RETRY_BACKOFF_SECONDS} --seed ${SEED} --worker-num-predict ${WORKER_NUM_PREDICT} --mentor-num-predict ${MENTOR_NUM_PREDICT} --results-path ${RESULTS_PATH}"

echo "[2/5] Running local verification benchmark"
if ! "${PYTHON_BIN}" -m mentor_worker_benchmark run \
  --task-pack "${TASK_PACK}" \
  --suite "${TASK_SUITE}" \
  --mentor-model "${MENTOR_MODEL}" \
  --worker-model "${WORKER_MODEL}" \
  --run-modes "${RUN_MODES}" \
  --repro \
  --max-turns "${MAX_TURNS}" \
  --model-timeout "${MODEL_TIMEOUT_SECONDS}" \
  --test-timeout "${TEST_TIMEOUT_SECONDS}" \
  --model-retries "${MODEL_RETRIES}" \
  --model-retry-backoff "${MODEL_RETRY_BACKOFF_SECONDS}" \
  --seed "${SEED}" \
  --worker-num-predict "${WORKER_NUM_PREDICT}" \
  --mentor-num-predict "${MENTOR_NUM_PREDICT}" \
  --results-path "${RESULTS_PATH}" 2>&1 | tee "${RUN_LOG_PATH}"; then
  echo "Local verification run failed. Completed units remain resumable via ${CHECKPOINT_PATH}." >&2
  tail -n 30 "${RUN_LOG_PATH}" >&2 || true
  exit 1
fi

echo "[3/5] Auditing artifact integrity"
"${PYTHON_BIN}" -m mentor_worker_benchmark audit "${RESULTS_PATH}"

echo "[4/5] Exporting community verification bundle"
"${PYTHON_BIN}" -m mentor_worker_benchmark export \
  --results "${RESULTS_PATH}" \
  --out "${SUBMISSION_PATH}" \
  --command "${RUN_COMMAND}"

echo "[5/5] Verifying community verification bundle"
"${PYTHON_BIN}" -m mentor_worker_benchmark verify --submission "${SUBMISSION_PATH}"

echo "Done."
echo "- Preflight JSON: ${PREFLIGHT_PATH}"
echo "- Results JSON: ${RESULTS_PATH}"
echo "- Checkpoint JSONL: ${CHECKPOINT_PATH}"
echo "- Run log: ${RUN_LOG_PATH}"
echo "- Verification ZIP: ${SUBMISSION_PATH}"
