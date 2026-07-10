"""Shared fixtures for AutoLand tests."""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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
