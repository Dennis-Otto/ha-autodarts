#!/usr/bin/env bash

# Verify the dashboard card in a real browser against a fresh demo instance.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PROJECT_NAME="${E2E_PROJECT_NAME:-autodarts_browser}"
# Keep the image version equal to playwright in requirements-browser.in.
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0"

export E2E_PROJECT_NAME="${PROJECT_NAME}"
# The same default as demo.sh, so the checks expect the board the demo starts.
export BOARD_MANAGER="${BOARD_MANAGER:-2}"
export E2E_PORT="${E2E_PORT:-18125}"
# Keep container paths unchanged and mount the Windows path when running from Git Bash.
export MSYS_NO_PATHCONV=1
ROOT_MOUNT="$(cd "${REPOSITORY_ROOT}" && (pwd -W 2>/dev/null || pwd))"
# Logs and screenshots of a failed run land here; CI uploads them.
ARTIFACTS="${E2E_ARTIFACTS:-${SCRIPT_DIR}/artifacts}"
mkdir -p "${ARTIFACTS}"
ARTIFACTS_MOUNT="$(cd "${ARTIFACTS}" && (pwd -W 2>/dev/null || pwd))"
COMPOSE=("${DOCKER_BIN}" compose --project-name "${PROJECT_NAME}" --file compose.yaml)

cleanup() {
	status=$?
	trap - EXIT
	if [[ "${status}" -ne 0 ]]; then
		"${COMPOSE[@]}" logs --no-color --tail 200 || true
		"${COMPOSE[@]}" exec -T homeassistant cat /config/home-assistant.log \
			>"${ARTIFACTS}/home-assistant-browser.log" 2>/dev/null || true
	fi
	"${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
	exit "${status}"
}
trap cleanup EXIT

# Relative Compose paths also work with Git Bash on Windows.
cd "${SCRIPT_DIR}"

bash "${SCRIPT_DIR}/demo.sh"
"${DOCKER_BIN}" run --rm --network "${PROJECT_NAME}_default" \
	--env "BOARD_MANAGER=${BOARD_MANAGER:-1}" \
	--env "BROWSER_ARTIFACTS=/artifacts" \
	--env "BROWSER_STEPS=${BROWSER_STEPS:-}" \
	--env "BROWSER_SCREENS=${BROWSER_SCREENS:-}" \
	--env "BROWSER_SCREENSHOTS=${BROWSER_SCREENSHOTS:-}" \
	--volume "${ROOT_MOUNT}:/repo:ro" \
	--volume "${ARTIFACTS_MOUNT}:/artifacts" \
	--workdir /repo/tests/e2e \
	"${PLAYWRIGHT_IMAGE}" \
	sh -c "pip install --quiet --disable-pip-version-check --root-user-action=ignore --break-system-packages --require-hashes -r requirements-browser.txt && python browser.py"
