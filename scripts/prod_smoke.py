#!/usr/bin/env python3
"""CLI: python scripts/prod_smoke.py --base-url https://jteam.ru"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jteam"))

from jteam.prod_smoke import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
