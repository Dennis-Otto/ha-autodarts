"""HACS installs the release package that the release workflow builds and signs."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_hacs_installs_the_signed_release_package():
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text("utf-8")
    assert hacs["zip_release"] is True
    package = hacs["filename"]
    assert f'--output="$RUNNER_TEMP/{package}"' in workflow
    assert f"subject-path: ${{{{ runner.temp }}}}/{package}" in workflow
    # HACS unpacks the archive into custom_components/autodarts, so it holds the
    # content of that folder without a folder around it.
    assert '"$GITHUB_SHA:custom_components/autodarts"' in workflow
