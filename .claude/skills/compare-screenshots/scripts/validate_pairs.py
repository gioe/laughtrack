#!/usr/bin/env python3
"""Stable skill entry point for delta-aware screenshot comparisons."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screenshots.comparison import (  # noqa: E402,F401
    PROFILE_ORDER,
    build_comparison,
    decoded_pixel_sha256,
    generate_sheets,
    main,
    write_reviewed_baseline,
)


# Preserve the old programmatic name while callers migrate to build_comparison.
build_view = build_comparison


if __name__ == "__main__":
    raise SystemExit(main())
