#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${DOCKER_IMAGE_TAG:-mentor-worker-benchmark:docker-sanity}"

docker build -t "${IMAGE_TAG}" "${ROOT_DIR}"
docker run --rm "${IMAGE_TAG}"
