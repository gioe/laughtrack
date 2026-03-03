"""Dashboard HTML generation package (modular replacement for legacy script).

Exposes a single public function:
    generate_html_dashboard(metrics: List[Dict[str, Any]], output_file: str) -> None

This mirrors the legacy API in `scripts/utils/generate_html_dashboard.py` while
the repository migrates callers. Internal structure is split across focused
modules (normalization, builders, renderer, generator) to enable future
extension (templating, theming, diff views, etc.).

Small‑chunk retirement plan:
1. Introduce modular implementation (this commit).
2. Point core service + scripts to this package instead of legacy script.
3. Turn legacy script into a thin shim (import + deprecation warning).
4. Delete legacy script after validation period.
"""

from .generator import generate_html_dashboard  # re-export

__all__ = ["generate_html_dashboard"]
