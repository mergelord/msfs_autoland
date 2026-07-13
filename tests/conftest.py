"""Shared fixtures for AutoLand tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Mock SimConnect and pyvjoy before any project module imports them at module level.
# In CI there is no SimConnect SDK or vJoy driver; tests use fakes/mocks exclusively.
for _mod in ('SimConnect', 'pyvjoy', 'pyvjoy._sdk'):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest
from tests.fakes import FakeAircraftAdapter, FakeClock, FakeControl, FakeVJoy


@pytest.fixture
def fake_control() -> FakeControl:
    return FakeControl()


@pytest.fixture
def fake_adapter() -> FakeAircraftAdapter:
    return FakeAircraftAdapter()


@pytest.fixture
def fake_vjoy() -> FakeVJoy:
    return FakeVJoy()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(start=1000.0)
