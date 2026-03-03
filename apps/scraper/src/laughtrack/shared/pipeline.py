"""Transformation pipeline facade to avoid deep imports and cycles.

We import the factory function directly from the implementation module,
not from the package __init__, to avoid circular partial initialization.
"""

from laughtrack.utilities.infrastructure.pipeline.pipeline import create_standard_pipeline  # noqa: F401
