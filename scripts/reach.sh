#!/usr/bin/env bash
# Prints this month's row of the reach table in docs/roadmap.md and
# docs/roadmap.de.md: the downloads of the package of every release, the unique
# visitors of the repository and those who came from Google in the last 14 days,
# whether Home Assistant's analytics list the integration, and the stars.
#
#   bash scripts/reach.sh      # the row of docs/roadmap.md
#   bash scripts/reach.sh de   # the row of docs/roadmap.de.md
#
# It needs the GitHub CLI, signed in with push access to the repository, because
# GitHub shows the visitors only to those who can push, curl and Python. It
# reads, and changes nothing.
set -euo pipefail

repository="${REACH_REPOSITORY:-Dennis-Otto/homedarts-for-autodarts}"
analytics="${REACH_ANALYTICS:-https://analytics.home-assistant.io/custom_integrations.json}"
python="$(command -v python3 || command -v python)"

# The answers go to files: the list of the analytics is too long for a variable
# of the environment.
answers="$(mktemp -d)"
trap 'rm -rf "${answers}"' EXIT
gh api --paginate --slurp "repos/${repository}/releases" >"${answers}/RELEASES"
gh api "repos/${repository}/traffic/views" >"${answers}/VIEWS"
gh api "repos/${repository}/traffic/popular/referrers" >"${answers}/REFERRERS"
gh api "repos/${repository}" >"${answers}/REPO"
curl --fail --silent --show-error --max-time 60 "${analytics}" >"${answers}/INTEGRATIONS"

REACH_LANGUAGE="${1:-en}" REACH_ANSWERS="${answers}" "${python}" - <<'PYTHON'
import datetime
import json
import os
from pathlib import Path


def read(name):
    return json.loads((Path(os.environ["REACH_ANSWERS"]) / name).read_text(encoding="utf-8"))


german = os.environ["REACH_LANGUAGE"] == "de"
releases = [release for page in read("RELEASES") for release in page]
# HACS installs and updates the integration from the homedarts.zip of a release,
# so its downloads count installations and updates, of the betas too; up to 1.18
# the file was autodarts.zip, after the former name of the integration.
downloads = sum(
    asset["download_count"]
    for release in releases
    for asset in release["assets"]
    if asset["name"] in ("homedarts.zip", "autodarts.zip")
)
visitors = read("VIEWS")["uniques"]
# GitHub names the referrer "Google", so the match ignores the case.
google = sum(
    referrer["uniques"]
    for referrer in read("REFERRERS")
    if "google" in referrer["referrer"].lower()
)
stars = read("REPO")["stargazers_count"]
# The analytics list every custom integration by its domain once an installation
# that shares its usage has it, with the versions installed: homedarts since 2.0,
# autodarts before. Other integrations for Autodarts use the domain autodarts too
# (see docs/coming-from.md), so only a version that is a release of this
# repository counts.
integrations = read("INTEGRATIONS")
versions = {
    version
    for domain in ("homedarts", "autodarts")
    for version in integrations.get(domain, {}).get("versions", {})
}
listed = bool({release["tag_name"].removeprefix("v") for release in releases} & versions)

today = datetime.date.today()
months = (
    "Januar Februar März April Mai Juni Juli August September Oktober November Dezember"
    if german
    else "January February March April May June July August September October November December"
).split()
answer = ("Ja", "Nein") if german else ("Yes", "No")
row = [f"{months[today.month - 1]} {today.year}", downloads, visitors, google]
row += [answer[0] if listed else answer[1], stars]
print("| " + " | ".join(map(str, row)) + " |")
PYTHON
