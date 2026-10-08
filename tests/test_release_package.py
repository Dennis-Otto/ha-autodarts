"""HACS installs the release package that the build of a release makes and signs."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_hacs_installs_the_signed_release_package():
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github" / "workflows" / "build-release.yml").read_text("utf-8")
    assert hacs["zip_release"] is True
    assert hacs["filename"] == "autodarts.zip"
    # The build of a release names the archive after hacs.json and attests every asset.
    assert "filename=\"$(jq -r '.filename // empty' hacs.json)\"" in workflow
    assert "subject-path: ${{ runner.temp }}/assets/*" in workflow
    # HACS unpacks the archive into custom_components/autodarts, so it holds the
    # content of that folder without a folder around it.
    assert '"HEAD:custom_components/$domain"' in workflow
