#!/usr/bin/env bash

# Regenerate the documentation images in docs/images from fresh demo instances.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PROJECT_NAME="${E2E_PROJECT_NAME:-autodarts_demo}"
# Keep the image version equal to playwright in requirements-browser.in.
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0"
ALPINE_IMAGE="alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8"

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
	"${DOCKER_BIN}" run --rm --network "${PROJECT_NAME}_default" \
		--env "DEMO_LANGUAGE=${language}" \
		--volume "${ROOT_MOUNT}:/repo" \
		--workdir /repo/tests/e2e \
		"${PLAYWRIGHT_IMAGE}" \
		sh -c "pip install --quiet --disable-pip-version-check --root-user-action=ignore --break-system-packages --require-hashes -r requirements-browser.txt && python screenshots.py"
done

# Shrink the screenshots to about a fifth without visible loss. pngquant exits
# with 98 or 99 when it keeps a file that would not get smaller or better.
"${DOCKER_BIN}" run --rm --volume "${ROOT_MOUNT}:/repo" "${ALPINE_IMAGE}" \
	sh -c "apk add --no-cache pngquant >/dev/null && { pngquant --force --skip-if-larger --strip --quality=80-95 --ext .png /repo/docs/images/*/*.png; status=\$?; [ \$status -eq 0 ] || [ \$status -eq 98 ] || [ \$status -eq 99 ]; }"
