from __future__ import annotations

from pathlib import Path

import pytest

from coachkg.config import REPO_ROOT
from coachkg.data import Exercise, load_exercises
from coachkg.kg.graph import NetworkXStore, build_movement_graph
from coachkg.kg.rules import RuleSet, load_rules

DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(autouse=True)
def _mock_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """The app defaults to Cognito auth; the offline suite runs as the local mock unless a test
    sets AUTH_MODE itself."""
    monkeypatch.setenv("AUTH_MODE", "mock")


@pytest.fixture(scope="session")
def data_dir() -> Path:
    if not (DATA_DIR / "exercises.json").exists():
        pytest.fail("data/ is missing: run `make data` (fetches the assessment inputs at a pinned commit)")
    return DATA_DIR


@pytest.fixture(scope="session")
def catalog(data_dir: Path) -> list[Exercise]:
    return load_exercises(data_dir)


@pytest.fixture(scope="session")
def rules(catalog: list[Exercise]) -> RuleSet:
    return load_rules(REPO_ROOT / "kg", catalog)


@pytest.fixture(scope="session")
def graph(catalog: list[Exercise], rules: RuleSet) -> NetworkXStore:
    return build_movement_graph(catalog, rules)
