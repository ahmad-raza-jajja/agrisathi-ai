"""Test-only launcher: runs the real app.py with a faked network (for screenshots / smoke tests)."""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["GEMINI_API_KEY"] = "fake-key-for-ui-test"
from tests import fake_gemini  # noqa: E402

fake_gemini.install()
runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
