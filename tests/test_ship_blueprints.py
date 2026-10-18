"""scripts/ship_blueprints.py copies the blueprints into the integration and keeps
the fingerprint of every version of each of them. A fingerprint never leaves the
file: without it, an unchanged earlier version would count as changed and would no
longer be updated."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from homeassistant.util.yaml import parse_yaml

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ship_blueprints", ROOT / "scripts" / "ship_blueprints.py"
)
ship = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ship)

LIGHTS = "blueprint:\n  name: Lights\n  domain: automation\n"
CALLER = "blueprint:\n  name: Caller\n  domain: automation\n"


def fingerprint(text: str) -> str:
    return ship.fingerprint(parse_yaml(text))


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    """A repository with two blueprints, an earlier shipped copy of one it no
    longer has, and the fingerprint of an earlier version of one of them."""
    source = tmp_path / ship.SOURCE
    source.mkdir(parents=True)
    (source / "lights.yaml").write_text(LIGHTS, encoding="utf-8")
    (source / "caller.yaml").write_text(CALLER, encoding="utf-8")
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    (shipped / "gone.yaml").write_text(CALLER, encoding="utf-8")
    versions = tmp_path / "blueprint_versions.json"
    versions.write_text(json.dumps({"lights.yaml": ["earlier"]}), encoding="utf-8")
    monkeypatch.setattr(ship, "ROOT", tmp_path)
    monkeypatch.setattr(ship, "SHIPPED", shipped)
    monkeypatch.setattr(ship, "VERSIONS", versions)
    monkeypatch.setattr(sys, "argv", ["ship_blueprints.py"])
    return tmp_path


def versions(repo: Path) -> dict[str, list[str]]:
    return json.loads((repo / "blueprint_versions.json").read_text(encoding="utf-8"))


def test_ships_each_blueprint_and_keeps_every_known_version(repo, capsys):
    ship.main()
    assert sorted(path.name for path in (repo / "shipped").iterdir()) == [
        "caller.yaml",
        "lights.yaml",
    ]
    assert (repo / "shipped" / "lights.yaml").read_text(encoding="utf-8") == LIGHTS
    expected = {
        "caller.yaml": [fingerprint(CALLER)],
        "lights.yaml": ["earlier", fingerprint(LIGHTS)],
    }
    assert versions(repo) == expected
    assert (repo / "blueprint_versions.json").read_bytes() == (
        json.dumps(expected, indent=2) + "\n"
    ).encode()
    assert "Shipped 2 blueprints" in capsys.readouterr().out
    # Once more: each version still once.
    ship.main()
    assert versions(repo) == expected


def test_a_new_version_is_added_after_the_earlier_ones(repo):
    ship.main()
    newer = LIGHTS.replace("Lights", "Light show")
    (repo / ship.SOURCE / "lights.yaml").write_text(newer, encoding="utf-8")
    ship.main()
    assert versions(repo)["lights.yaml"] == [
        "earlier",
        fingerprint(LIGHTS),
        fingerprint(newer),
    ]


def test_starts_without_a_file_of_versions(repo):
    (repo / "blueprint_versions.json").unlink()
    ship.main()
    assert versions(repo)["lights.yaml"] == [fingerprint(LIGHTS)]


def test_the_history_adds_every_version_in_git(repo, monkeypatch):
    calls = []

    def git(*args: str) -> str:
        calls.append(args)
        if args[0] == "log":
            return "first\nsecond\n" if "lights" in args[-1] else ""
        return {"first": CALLER, "second": LIGHTS}[args[1].split(":")[0]]

    monkeypatch.setattr(ship, "_git", git)
    monkeypatch.setattr(sys, "argv", ["ship_blueprints.py", "--history"])
    ship.main()
    assert versions(repo)["lights.yaml"] == [
        fingerprint(CALLER),
        fingerprint(LIGHTS),
        "earlier",
    ]
    path = (ship.SOURCE / "lights.yaml").as_posix()
    assert ("log", "--reverse", "--format=%H", "HEAD", "--", path) in calls
    assert ("show", f"first:{path}") in calls


# Reads the history of the repository, which mutmut's copy has not.
@pytest.mark.mutation_unsafe
def test_no_version_of_a_blueprint_in_git_is_forgotten():
    known = json.loads(ship.VERSIONS.read_text(encoding="utf-8"))
    for name in known:
        missing = set(ship.history(name)) - set(known[name])
        assert not missing, (
            f"{name} lost fingerprints of earlier versions. "
            "Run python scripts/ship_blueprints.py --history"
        )
