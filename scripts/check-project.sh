#!/usr/bin/env bash
# The checks of this integration alone, which scripts/check.sh runs last: the license
# terms, and the tests of the dashboard cards and of the translation bot with Node (100 %
# of lines, branches and functions covered).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

printf '\n== %s\n' "The license"
python3 - <<'PYTHON'
import hashlib
from pathlib import Path

for path in ("LICENSE", "custom_components/autodarts/LICENSE"):
	text = Path(path).read_text(encoding="utf-8")
	if not text.startswith("MIT License\n") or "Copyright (c)" not in text:
		raise SystemExit(f"{path}: the MIT license and its copyright must stay.")
	terms = text[text.index("Permission is hereby granted"):]
	digest = hashlib.sha256(" ".join(terms.split()).encode()).hexdigest()
	# The MIT grant and disclaimer, whatever the names and the wrapping.
	if digest != "fe2a9817987f862eaced948f0468c7f51d2fedfc48c5c505b246a49a3870e9a5":
		raise SystemExit(f"{path}: the terms differ from the MIT license.")
print("LICENSE and the copy in the integration carry the MIT terms.")
PYTHON

printf '\n== %s\n' "The cards and the translation bot"
if ! command -v node >/dev/null 2>&1 || [[ ! -d node_modules ]]; then
	# The CI sets up Node and runs npm ci, so there a missing one is an error.
	if [[ -n "${CI:-}" ]]; then
		echo "Node.js or the packages of npm ci are missing." >&2
		exit 1
	fi
	echo "Node.js or its packages (npm ci) are missing here; the CI tests the cards."
	exit 0
fi
node --check custom_components/autodarts/frontend/autodarts-card.js
npm test
