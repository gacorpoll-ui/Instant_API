"""Allow `python -m instantapi` to run the CLI."""

import os
import sys

# Force UTF-8 on Windows before anything else
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from instantapi.cli import app

if __name__ == "__main__":
    app()
