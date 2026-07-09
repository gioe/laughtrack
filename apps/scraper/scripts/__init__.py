"""Scripts package.

Importing laughtrack.adapters.db here wires the concrete database adapter into
the core.data.base_handler seam for every python -m scripts.* entry point —
core cannot import the adapters layer directly (core.entities import-linter
contract), so the binding happens at the composition roots: this package init
for scripts, laughtrack.app.wiring for the app layer (TASK-3701).
"""

import laughtrack.adapters.db  # noqa: F401
