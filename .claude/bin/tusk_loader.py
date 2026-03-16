"""Dynamic module loader for hyphenated tusk script filenames.

Python cannot import modules with hyphens in their names via normal import
statements. This loader provides a `load()` function that imports them by
path so other tusk scripts can share code from tusk-db-lib.py etc.

Usage:
    import tusk_loader
    _db_lib = tusk_loader.load("tusk-db-lib")
"""

import importlib.util
import os


def load(module_name: str):
    """Load a tusk-*.py module by its hyphenated name (without .py extension).

    Args:
        module_name: The hyphenated module name, e.g. "tusk-db-lib"

    Returns:
        The loaded module object.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, f"{module_name}.py")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module '{module_name}' from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
