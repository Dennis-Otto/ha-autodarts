#!/usr/bin/env bash

# Regenerate the documentation images in docs/images from fresh demo instances.
# The demo's clock stands still at DEMO_TIME and its random numbers are fixed, so
# that two runs render the same images, byte for byte.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PROJECT_NAME="${E2E_PROJECT_NAME:-autodarts_demo}"
# Keep the image version equal to playwright in requirements-browser.in.
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0"
# A Tuesday evening, three days after the highlight photos of the demo.
export DEMO_TIME="${DEMO_TIME:-2026-09-29T20:30:00+02:00}"

export E2E_PROJECT_NAME="${PROJECT_NAME}"
# Keep container paths unchanged and mount the Windows path when running from Git Bash.
export MSYS_NO_PATHCONV=1
ROOT_MOUNT="$(cd "${REPOSITORY_ROOT}" && (pwd -W 2>/dev/null || pwd))"

cleanup() {
	"${DOCKER_BIN}" compose --project-name "${PROJECT_NAME}" --file compose.yaml \
		down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Relative Compose paths also work with Git Bash on Windows.
cd "${SCRIPT_DIR}"

for language in ${LANGUAGES:-en de}; do
	DEMO_LANGUAGE="${language}" bash "${SCRIPT_DIR}/demo.sh"
	# The config volume of the demo holds the file that moves its frozen clock on.
	"${DOCKER_BIN}" run --rm --network "${PROJECT_NAME}_default" \
		--env "DEMO_LANGUAGE=${language}" \
		--env "DEMO_TIME=${DEMO_TIME}" \
		--env "DEMO_CLOCK=/ha-config/.demo_clock" \
		--env "KEEP_RAW=${KEEP_RAW:-}" \
		--volume "${ROOT_MOUNT}:/repo" \
		--volume "${PROJECT_NAME}_homeassistant_config:/ha-config" \
		--workdir /repo/tests/e2e \
		"${PLAYWRIGHT_IMAGE}" \
		sh -c "bash pngquant.sh && pip install --quiet --disable-pip-version-check --root-user-action=ignore --break-system-packages --require-hashes -r requirements-browser.txt && python screenshots.py"
done
