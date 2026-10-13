#!/usr/bin/env bash

# Verify the dashboard card in a real browser against a fresh demo instance.
#
# BROWSER_SHARD=k/n runs the k-th of n parts of the steps (see shards.py), and
# BROWSER_WORKERS=W runs that part on W demo instances side by side, each with a
# browser and a shard of its own: worker w takes the shard (k - 1) * W + w of n * W.
# So BROWSER_WORKERS=4 runs every step on one machine in about a quarter of the time,
# and BROWSER_SHARD=2/2 with BROWSER_WORKERS=2, as in CI, the shards 3/4 and 4/4.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PROJECT_NAME="${E2E_PROJECT_NAME:-autodarts_browser}"
# Keep the image version equal to playwright in requirements-browser.in.
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0"

# The same default as demo.sh, so the checks expect the board the demo starts.
export BOARD_MANAGER="${BOARD_MANAGER:-2}"
PORT="${E2E_PORT:-18125}"
WORKERS="${BROWSER_WORKERS:-1}"
SHARD="${BROWSER_SHARD:-1/1}"
if [[ ! "${WORKERS}" =~ ^[1-9][0-9]*$ ]]; then
	echo "BROWSER_WORKERS is a number of at least 1, not '${WORKERS}'" >&2
	exit 2
fi
if [[ ! "${SHARD}" =~ ^([1-9][0-9]*)/([1-9][0-9]*)$ ]] || ((BASH_REMATCH[1] > BASH_REMATCH[2])); then
	echo "BROWSER_SHARD is k/n with 1 <= k <= n, such as 2/4, not '${SHARD}'" >&2
	exit 2
fi
PART="${BASH_REMATCH[1]}"
PARTS="${BASH_REMATCH[2]}"
# Keep container paths unchanged and mount the Windows path when running from Git Bash.
export MSYS_NO_PATHCONV=1
ROOT_MOUNT="$(cd "${REPOSITORY_ROOT}" && (pwd -W 2>/dev/null || pwd))"
# Logs and screenshots of a failed run land here, with several workers in a folder per
# worker; CI uploads them.
ARTIFACTS="${E2E_ARTIFACTS:-${SCRIPT_DIR}/artifacts}"
mkdir -p "${ARTIFACTS}"

# The shard, Compose project and artifacts of a worker. One worker keeps the project,
# port and folder of a run without workers; the others take the next ports.
shard_of() { echo "$(((PART - 1) * WORKERS + $1))/$((PARTS * WORKERS))"; }
project_of() { if ((WORKERS == 1)); then echo "${PROJECT_NAME}"; else echo "${PROJECT_NAME}_$1"; fi; }
artifacts_of() {
	local shard
	shard="$(shard_of "$1")"
	if ((WORKERS == 1)); then echo "${ARTIFACTS}"; else echo "${ARTIFACTS}/shard-${shard/\//-of-}"; fi
}
compose_of() { "${DOCKER_BIN}" compose --project-name "$(project_of "$1")" --file compose.yaml "${@:2}"; }

# The workers that failed, when several run side by side.
FAILED=()

cleanup() {
	status=$?
	trap - EXIT
	local worker folder
	for ((worker = 1; worker <= WORKERS; worker++)); do
		folder="$(artifacts_of "${worker}")"
		# In CI, the summary of the job shows the seconds of every step, which
		# browser.py writes after each one, also after a failed step.
		if [[ -n "${GITHUB_STEP_SUMMARY:-}" && -s "${folder}/browser-steps-table.md" ]]; then
			cat "${folder}/browser-steps-table.md" >>"${GITHUB_STEP_SUMMARY}" || true
		fi
		if ((status != 0)) && { ((WORKERS == 1)) || [[ " ${FAILED[*]} " == *" ${worker} "* ]]; }; then
			compose_of "${worker}" logs --no-color --tail 200 || true
			compose_of "${worker}" exec -T homeassistant cat /config/home-assistant.log \
				>"${folder}/home-assistant-browser.log" 2>/dev/null || true
		fi
		compose_of "${worker}" down --volumes --remove-orphans >/dev/null 2>&1 || true
	done
	exit "${status}"
}
trap cleanup EXIT

# One worker: its demo instance, then its shard of the steps in the Playwright image.
worker() {
	local folder artifacts_mount
	folder="$(artifacts_of "$1")"
	mkdir -p "${folder}"
	rm -f "${folder}/browser-steps-table.md"
	artifacts_mount="$(cd "${folder}" && (pwd -W 2>/dev/null || pwd))"
	E2E_PROJECT_NAME="$(project_of "$1")" E2E_PORT="$((PORT + $1 - 1))" \
		bash "${SCRIPT_DIR}/demo.sh"
	"${DOCKER_BIN}" run --rm --network "$(project_of "$1")_default" \
		--env "BOARD_MANAGER=${BOARD_MANAGER}" \
		--env "BROWSER_ARTIFACTS=/artifacts" \
		--env "BROWSER_SHARD=$(shard_of "$1")" \
		--env "BROWSER_STEPS=${BROWSER_STEPS:-}" \
		--env "BROWSER_SCREENS=${BROWSER_SCREENS:-}" \
		--env "BROWSER_SCREENSHOTS=${BROWSER_SCREENSHOTS:-}" \
		--volume "${ROOT_MOUNT}:/repo:ro" \
		--volume "${artifacts_mount}:/artifacts" \
		--workdir /repo/tests/e2e \
		"${PLAYWRIGHT_IMAGE}" \
		sh -c "pip install --quiet --disable-pip-version-check --root-user-action=ignore --break-system-packages --require-hashes -r requirements-browser.txt && python browser.py"
}

# Every line of a worker, marked with its shard.
label() {
	local line
	while IFS= read -r line || [[ -n "${line}" ]]; do
		printf '[%s] %s\n' "$1" "${line}"
	done
}

# Relative Compose paths also work with Git Bash on Windows.
cd "${SCRIPT_DIR}"

# Both images at once, before the demo starts: Home Assistant's for the demo and its
# board, and Playwright's, which would otherwise wait for the demo.
started="${SECONDS}"
compose_of 1 pull --quiet --policy missing &
pulling=$!
if ! "${DOCKER_BIN}" image inspect "${PLAYWRIGHT_IMAGE}" >/dev/null 2>&1; then
	"${DOCKER_BIN}" pull --quiet "${PLAYWRIGHT_IMAGE}" >/dev/null
fi
wait "${pulling}"
echo "Images ready in $((SECONDS - started)) s"

if ((WORKERS == 1)); then
	worker 1
	exit 0
fi
workers=()
for ((w = 1; w <= WORKERS; w++)); do
	(worker "${w}" 2>&1 | label "$(shard_of "${w}")") &
	workers+=("$!")
done
# Every worker runs to its end, so that a run names all the shards that fail.
for ((w = 1; w <= WORKERS; w++)); do
	wait "${workers[w - 1]}" || FAILED+=("${w}")
done
if ((${#FAILED[@]} > 0)); then
	for w in "${FAILED[@]}"; do
		echo "The browser check failed in shard $(shard_of "${w}"); its lines begin with [$(shard_of "${w}")]."
	done
	exit 1
fi
