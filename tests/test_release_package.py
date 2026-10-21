"""HACS installs the release package that the build of a release makes and signs."""

import json
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_hacs_installs_the_signed_release_package():
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github" / "workflows" / "build-release.yml").read_text("utf-8")
    assert hacs["zip_release"] is True
    assert hacs["filename"] == "homedarts.zip"
    # The build of a release names the archive after hacs.json and attests every asset.
    assert "filename=\"$(jq -r '.filename // empty' hacs.json)\"" in workflow
    assert "subject-path: ${{ runner.temp }}/assets/*" in workflow
    # HACS unpacks the archive into custom_components/homedarts, so it holds the
    # content of that folder without a folder around it.
    assert '"HEAD:custom_components/$domain"' in workflow


def test_the_release_package_carries_the_blueprints():
    """The integration installs the blueprints from its own folder, the content of
    the package, so no rule of .gitattributes may leave them out of the archive."""
    integration = Path("custom_components", "homedarts")
    shipped = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / integration / "blueprints").rglob("*.yaml")
    ]
    assert len(shipped) == len(list((ROOT / "blueprints").rglob("*.yaml")))
    shipped.append((integration / "blueprint_versions.json").as_posix())
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    for line in attributes:
        if "export-ignore" in line.split()[1:]:
            pattern = line.split()[0]
            assert not [
                path
                for path in shipped
                if fnmatch(path, pattern) or fnmatch(Path(path).name, pattern)
            ], line
