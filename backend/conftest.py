import sys
import os

# Add the backend root directory to Python's path so that
# "from app.agents.xxx import xxx" works in all test files.
# Without this, pytest runs from inside the tests/ folder and
# can't find the app/ package — hence ModuleNotFoundError: No module named 'app'
sys.path.insert(0, os.path.dirname(__file__))

import pytest


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + (tmp_path / "applications.db").as_posix())
