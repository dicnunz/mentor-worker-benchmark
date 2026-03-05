#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

BOOTSTRAP_PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

PROTOCOL_VERSION="${PROTOCOL_VERSION:-v0.3.0}"
CANONICAL_WORKER_MODELS="${CANONICAL_WORKER_MODELS:-phi3:mini,qwen2.5-coder:7b}"
CANONICAL_MENTOR_MODELS="${CANONICAL_MENTOR_MODELS:-llama3.1:8b,mistral:7b}"
CANONICAL_MODELS="${CANONICAL_MODELS:-${CANONICAL_WORKER_MODELS},${CANONICAL_MENTOR_MODELS}}"

SEEDS="${SEEDS:-1337}"
RUN_MODES="${RUN_MODES:-worker_only,mentor_worker}"
MAX_TURNS="${MAX_TURNS:-3}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-180}"
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT:-512}"
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT:-256}"

RESULTS_PATH="${RESULTS_PATH:-results/reproducible_quick_protocol-${PROTOCOL_VERSION}_results.json}"
RUN_LOG_PATH="${RUN_LOG_PATH:-results/reproducible_quick_protocol-${PROTOCOL_VERSION}_run.log}"
STAMP="$(date +%F)"
SEEDS_TOKEN="${SEEDS//,/-}"
SUBMISSION_PATH="${SUBMISSION_PATH:-submissions/reproducible_quick_protocol-${PROTOCOL_VERSION}_seeds-${SEEDS_TOKEN}_${STAMP}.zip}"

echo "[1/5] Installing dependencies"
if ! command -v "${BOOTSTRAP_PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${BOOTSTRAP_PYTHON_BIN}" >&2
  exit 1
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  "${BOOTSTRAP_PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

"${PIP_BIN}" install --upgrade pip
"${PIP_BIN}" install -r requirements.lock
"${PIP_BIN}" install -e .

echo "[2/5] Verifying Ollama models"
"${PYTHON_BIN}" -m mentor_worker_benchmark setup --models "${CANONICAL_MODELS}"

echo "[3/5] Running canonical quick benchmark"
PYTHON_BIN="${PYTHON_BIN}" \
PROTOCOL_VERSION="${PROTOCOL_VERSION}" \
WORKER_MODELS="${CANONICAL_WORKER_MODELS}" \
MENTOR_MODELS="${CANONICAL_MENTOR_MODELS}" \
RUN_MODES="${RUN_MODES}" \
MAX_TURNS="${MAX_TURNS}" \
TIMEOUT_SECONDS="${TIMEOUT_SECONDS}" \
SEEDS="${SEEDS}" \
WORKER_NUM_PREDICT="${WORKER_NUM_PREDICT}" \
MENTOR_NUM_PREDICT="${MENTOR_NUM_PREDICT}" \
RESULTS_PATH="${RESULTS_PATH}" \
RUN_LOG_PATH="${RUN_LOG_PATH}" \
SUBMISSION_PATH="${SUBMISSION_PATH}" \
./scripts/run_official_quick.sh

echo "[4/5] Rebuilding community leaderboard artifacts"
"${PYTHON_BIN}" scripts/build_community_leaderboard.py --strict

echo "[5/5] Auditing benchmark artifact integrity"
"${PYTHON_BIN}" -m mentor_worker_benchmark audit "${RESULTS_PATH}"

echo "Reproducibility pipeline completed successfully."
echo "- Results: ${RESULTS_PATH}"
echo "- Run log: ${RUN_LOG_PATH}"
echo "- Submission ZIP: ${SUBMISSION_PATH}"
