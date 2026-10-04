"""Compatibility entry point; the maintained application lives in ../../app."""
import runpy
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_DIR))
if __name__ == "__main__":
    runpy.run_path(str(APP_DIR / "main.py"), run_name="__main__")
