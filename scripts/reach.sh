#!/usr/bin/env bash
# Prints this month's row of the reach table in docs/roadmap.md and
# docs/roadmap.de.md: the downloads of the package of every release, the unique
# visitors of the repository and those who came from Google in the last 14 days,
# whether Home Assistant's analytics list the integration, and the stars.
#
#   bash scripts/reach.sh
#
# It needs the GitHub CLI, signed in with push access to the repository, because
# GitHub shows the visitors only to those who can push, and curl. It reads, and
# changes nothing.
set -euo pipefail

repository="${REACH_REPOSITORY:-Dennis-Otto/ha-autodarts}"
analytics="https://analytics.home-assistant.io/custom_integrations.json"

# HACS installs and updates the integration from the autodarts.zip of a release,
# so its downloads count installations and updates, of the betas too. --paginate
# prints one sum per page of releases.
downloads="$(gh api --paginate "repos/${repository}/releases" \
  --jq '[.[].assets[] | select(.name == "autodarts.zip") | .download_count] | add // 0' |
  awk '{ sum += $1 } END { print sum + 0 }')"
visitors="$(gh api "repos/${repository}/traffic/views" --jq '.uniques')"
google="$(gh api "repos/${repository}/traffic/popular/referrers" \
  --jq '[.[] | select(.referrer | test("google")) | .uniques] | add // 0')"
stars="$(gh api "repos/${repository}" --jq '.stargazers_count')"
# The analytics list every custom integration by its domain once an installation
# that shares its usage has it. The list is read whole first: grep -q would stop
# reading at the first match, and curl would fail on the closed pipe.
listed="No"
integrations="$(curl --fail --silent --show-error --max-time 60 "${analytics}")"
if grep -q '"autodarts":' <<<"${integrations}"; then
  listed="Yes"
fi

printf '| %s | %s | %s | %s | %s | %s |\n' \
  "$(LC_ALL=C date +'%B %Y')" "${downloads}" "${visitors}" "${google}" "${listed}" "${stars}"
