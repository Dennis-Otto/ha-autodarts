#!/usr/bin/env bash

# Render the documentation images anew with the frozen clock of the demo and compare
# them with the committed ones, pixel by pixel. Afterwards docs/images holds the new
# images, and tests/e2e/artifacts/visual/ the report of compare.py: report.json,
# summary.md and every changed image before and after, with its difference. With
# RESTORE=1, an image whose pixels did not change keeps its committed file. The
# visual check of pull requests (visual.yml) and the screenshot bot (screenshots.yml)
# run it; LANGUAGES chooses the languages, as for screenshots.sh.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
# Keep the image version equal to playwright in requirements-browser.in.
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0"
REFERENCE="${SCRIPT_DIR}/artifacts/visual-reference"
OUTPUT="${SCRIPT_DIR}/artifacts/visual"
export LANGUAGES="${LANGUAGES:-en de}"
# Keep container paths unchanged and mount the Windows path when running from Git Bash.
export MSYS_NO_PATHCONV=1
ROOT_MOUNT="$(cd "${REPOSITORY_ROOT}" && (pwd -W 2>/dev/null || pwd))"

rm -rf "${REFERENCE}" "${OUTPUT}"
mkdir -p "${REFERENCE}" "${OUTPUT}"
cp -R "${REPOSITORY_ROOT}/docs/images/." "${REFERENCE}/"

bash "${SCRIPT_DIR}/screenshots.sh"

options=(--languages "$(tr ' ' ',' <<<"${LANGUAGES}")")
if [[ -n "${RESTORE:-}" ]]; then
	options+=(--restore)
fi
"${DOCKER_BIN}" run --rm \
	--volume "${ROOT_MOUNT}:/repo" \
	--workdir /repo/tests/e2e \
	"${PLAYWRIGHT_IMAGE}" \
	sh -c "pip install --quiet --disable-pip-version-check --root-user-action=ignore --break-system-packages --require-hashes -r requirements-browser.txt && python compare.py artifacts/visual-reference ../../docs/images artifacts/visual ${options[*]}"
