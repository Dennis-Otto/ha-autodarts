"""The tests work under mutmut, the tool of the weekly mutation tests: in its copy of
the repository, several times in its first process, and in the process of each
mutant, which it forks from that first one."""

import ast
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.autodarts import checkout

from .conftest import (
    MODULES,
    clear_integration_caches,
    hypothesis_profile,
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

    def __init__(self, *markers) -> None:
        self.markers = [
            (getattr(pytest.mark, marker) if isinstance(marker, str) else marker).mark
            for marker in markers
        ]

    def get_closest_marker(self, name: str):
        return next((mark for mark in self.markers if mark.name == name), None)

    def add_marker(self, marker, append: bool = True) -> None:
        if append:
            self.markers.append(marker.mark)
        else:
            self.markers.insert(0, marker.mark)


# The configuration of pytest, with the time limit of pyproject.toml.
CONFIG = SimpleNamespace(getini={"timeout": "30"}.get)


def collected(*markers) -> Item:
    """A test with these markers, as the collection leaves it."""
    item = Item(*markers)
    pytest_collection_modifyitems(CONFIG, [item])
    return item


def skipped(*markers: str) -> bool:
    """Whether the collection skips a test with these markers."""
    return collected(*markers).get_closest_marker("skip") is not None


def time_limit(*markers) -> float | None:
    """The time limit of a test with these markers, as the collection leaves it."""
    limit = collected(*markers).get_closest_marker("timeout")
    return limit.args[0] if limit else None


def test_mutmut_skips_the_tests_that_fail_in_its_copy(monkeypatch):
    monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    assert not skipped("mutation_unsafe")
    # Every run of mutmut sets the variable, the one without a mutant to nothing.
    for mutant in ("", "stats", "custom_components.autodarts.checkout.x__mutmut_1"):
        monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
        assert skipped("mutation_unsafe")
        assert not skipped()
        assert not skipped("expected_errors")


def test_mutmut_gives_every_test_ten_times_its_time_limit(monkeypatch):
    monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    assert time_limit() is None
    assert time_limit(pytest.mark.timeout(180)) == 180
    monkeypatch.setenv("MUTANT_UNDER_TEST", "stats")
    assert time_limit() == 300
    assert time_limit(pytest.mark.timeout(180)) == 1800
    assert time_limit("mutation_unsafe") == 300
    # Without a time limit there is none under mutmut either.
    monkeypatch.setattr(CONFIG, "getini", {"timeout": ""}.get)
    assert time_limit() == 0


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


@pytest.mark.mutation_unsafe  # asks Git
def test_mutmut_copies_every_file_and_folder_of_the_repository():
    # A file that a new test reads and that is missing in mutants/ fails the run of
    # mutmut before its first mutant, so a new one joins also_copy at once.
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout
    top_level = {path.split("/")[0] for path in tracked.split("\0") if path}
    assert set(MUTMUT["also_copy"]) == top_level - {"custom_components"}
    assert MUTMUT["also_copy"] == sorted(MUTMUT["also_copy"])


def decorators(path: Path) -> set[str]:
    """The names of the decorators of the functions of a module."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    decorator = decorator.func
                names.add(ast.unparse(decorator))
    return names


@pytest.mark.mutation_unsafe  # reads the code as text
def test_mutmut_changes_the_functions_with_a_cache():
    # mutmut leaves a decorated function unchanged, apart from static and class
    # methods, so a cache wraps its function instead: f = lru_cache()(_uncached_f).
    for path in MUTMUT["only_mutate"]:
        assert decorators(ROOT / path) <= {
            "abstractmethod",
            "classmethod",
            "property",
            "staticmethod",
        }, path
    assert decorators(ROOT / "custom_components/autodarts/checkout.py") == {"property"}


def test_the_property_tests_draw_the_same_examples_in_ci_and_under_mutmut():
    assert hypothesis_profile({}) == "local"
    assert hypothesis_profile({"CI": ""}) == "local"
    assert hypothesis_profile({"CI": "true"}) == "ci"
    # mutmut sets the variable in each of its runs, the one without a mutant to "".
    assert hypothesis_profile({"MUTANT_UNDER_TEST": ""}) == "ci"
    assert hypothesis_profile({"MUTANT_UNDER_TEST": "stats"}) == "ci"
