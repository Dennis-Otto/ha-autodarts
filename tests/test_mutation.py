"""The tests work under mutmut, the tool of the weekly mutation tests: in its copy of
the repository, once per mutant in the same process, and in processes forked from
one that ran them all."""

import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.autodarts import checkout

from .conftest import (
    MODULES,
    clear_integration_caches,
    module_caches,
    pytest_collection_modifyitems,
    pytest_runtest_call,
)

ROOT = Path(__file__).parents[1]
MUTMUT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
    "mutmut"
]


class Item:
    """A collected test with its markers."""

    def __init__(self, *markers: str) -> None:
        self.markers = [getattr(pytest.mark, name).mark for name in markers]

    def get_closest_marker(self, name: str):
        return next((mark for mark in self.markers if mark.name == name), None)

    def add_marker(self, marker) -> None:
        self.markers.append(marker.mark)


def skipped(*markers: str) -> bool:
    """Whether the collection skips a test with these markers."""
    item = Item(*markers)
    pytest_collection_modifyitems(None, [item])
    return item.get_closest_marker("skip") is not None


def test_mutmut_skips_the_tests_that_fail_in_its_copy(monkeypatch):
    monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    assert not skipped("mutation_unsafe")
    # Every run of mutmut sets the variable, the one without a mutant to nothing.
    for mutant in ("", "stats", "custom_components.autodarts.checkout.x__mutmut_1"):
        monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
        assert skipped("mutation_unsafe")
        assert not skipped()
        assert not skipped("expected_errors")


def run(params, test) -> None:
    """Runs a test with these parameters as pytest does, with the check of the
    parameters around it."""
    hook = pytest_runtest_call(SimpleNamespace(callspec=SimpleNamespace(params=params)))
    next(hook)
    test()
    with pytest.raises(StopIteration):
        hook.send(None)


def test_a_test_that_changes_its_parameters_fails():
    setup = {"remaining": 32, "hold": True}
    run({"setup": setup, "points": 100}, lambda: dict(setup).pop("remaining"))
    with pytest.raises(pytest.fail.Exception, match="changed its parameters"):
        run({"setup": setup, "points": 100}, lambda: setup.pop("remaining"))
    # A test without parameters has nothing to change.
    hook = pytest_runtest_call(SimpleNamespace())
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(None)


def test_every_test_starts_with_the_caches_of_the_integration_empty():
    cached = (checkout.checkout, checkout.setup, checkout._leave_ranks)
    assert "custom_components.autodarts.checkout" in MODULES
    assert set(module_caches(checkout)) == set(cached)
    # Emptied before this test, whichever tests ran before it.
    assert [function.cache_info().currsize for function in cached] == [0, 0, 0]
    checkout.setup(171)
    assert all(function.cache_info().currsize for function in cached)
    clear_integration_caches()
    assert [function.cache_info().currsize for function in cached] == [0, 0, 0]


def test_mutmut_mutates_and_copies_files_that_exist():
    assert MUTMUT["source_paths"] == ["custom_components"]
    assert MUTMUT["only_mutate"] == sorted(MUTMUT["only_mutate"])
    for path in MUTMUT["only_mutate"]:
        assert (ROOT / path).is_file(), path
    for path in MUTMUT["also_copy"]:
        assert (ROOT / path).exists(), path
    # mutmut copies the integration as the code it mutates, before the other files.
    assert "custom_components" not in MUTMUT["also_copy"]
    assert "tests" in MUTMUT["also_copy"]
