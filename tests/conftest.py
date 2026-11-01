import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
DEVELOPMENT = ["development_small", "development_medium", "development_large"]


def run_tool(*args: str) -> subprocess.CompletedProcess:
    """Run a module command (e.g. `pfsp solve ...`) the way the documented tasks do."""
    return subprocess.run(
        [sys.executable, "-m", *args], capture_output=True, text=True, check=False
    )


@pytest.fixture
def copy_instance(tmp_path):
    """Copy a supplied instance directory to a fresh path, as the instructor does."""

    def _copy(name: str) -> Path:
        target = tmp_path / f"fresh_{name}"
        shutil.copytree(DATA / name, target)
        return target

    return _copy
