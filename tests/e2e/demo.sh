#!/usr/bin/env bash

# Start a disposable demo instance with a simulated board and the Autodarts card.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
E2E_PORT="${E2E_PORT:-18124}"
PROJECT_NAME="${E2E_PROJECT_NAME:-autodarts_demo}"
COMPOSE=("${DOCKER_BIN}" compose --project-name "${PROJECT_NAME}" --file compose.yaml --file compose.demo.yaml)
# The screenshots freeze the clock at DEMO_TIME, such as 2026-09-29T20:30:00+02:00
# (see frozen/sitecustomize.py).
if [[ -n "${DEMO_TIME:-}" ]]; then
	COMPOSE+=(--file compose.frozen.yaml)
	export DEMO_TIME
fi

export E2E_PORT
export DEMO_LANGUAGE="${DEMO_LANGUAGE:-en}"
# The demo shows the current headless Board Manager 2 unless told otherwise.
export BOARD_MANAGER="${BOARD_MANAGER:-2}"
# Keep container paths such as /e2e unchanged when running from Git Bash on Windows.
export MSYS_NO_PATHCONV=1

cd "${SCRIPT_DIR}"
"${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
"${COMPOSE[@]}" up --detach --wait --wait-timeout 300
if ! "${COMPOSE[@]}" exec -T homeassistant python3 /e2e/demo.py; then
	"${COMPOSE[@]}" logs --no-color --tail 200 || true
	exit 1
fi

echo "Demo ready: http://127.0.0.1:${E2E_PORT}/autodarts-demo/board"
echo "Stop it with: docker compose --project-name ${PROJECT_NAME} --file ${SCRIPT_DIR}/compose.yaml down --volumes"
