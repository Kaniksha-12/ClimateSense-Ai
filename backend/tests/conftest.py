import os
import tempfile
from pathlib import Path

_TEST_DATABASE_DIRECTORY = tempfile.TemporaryDirectory(prefix="climatesense-tests-")
_TEST_DATABASE_PATH = Path(_TEST_DATABASE_DIRECTORY.name) / "test.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE_PATH}"


def pytest_sessionfinish(session, exitstatus) -> None:
    from app.db.database import engine

    engine.dispose()
    _TEST_DATABASE_DIRECTORY.cleanup()
