import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODEL = "gemini-3.5-flash-lite"
TOP_DAYS = 5
MAX_ROWS = 50
EXAMPLE_ROWS = 3
CLASSIFIER_BATCH = 150
MAX_TOOL_CALLS = 20


def data_dir():
    return Path(os.environ.get("BOOKSTORE_DATA_DIR", ROOT / "data"))


def clean_dir():
    return Path(os.environ.get("BOOKSTORE_CLEAN_DIR", ROOT / "clean"))


def results_dir():
    return ROOT / "results"
