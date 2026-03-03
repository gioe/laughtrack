"""Scraper registry.

Provides a mapping from scraper key -> scraper class.
Lives in app so nothing imports it downward, avoiding cycles.

Discovery strategy:
- Dynamically import all modules that match laughtrack.scrapers.implementations.*.scraper
- This avoids importing package __init__ files that can create cycles
- After preloading, walk BaseScraper.__subclasses__ to build the registry
"""

from typing import Any, Dict, Type
import importlib
import pkgutil


def _preload_scraper_modules() -> None:
    """Import all scraper modules to ensure subclasses are registered.

    We only import modules named 'scraper' under the implementations tree
    to prevent importing package-level __init__ files that may re-export
    broader symbols and introduce cycles.
    """
    try:
        import laughtrack.scrapers.implementations as impl_pkg
    except Exception:
        return

    # Safely access package search path
    pkg_name = getattr(impl_pkg, "__name__", "laughtrack.scrapers.implementations")
    pkg_paths = getattr(impl_pkg, "__path__", None)
    if not pkg_paths:
        return

    prefix = pkg_name + "."
    for _, modname, ispkg in pkgutil.walk_packages(pkg_paths, prefix):
        # Only import leaf modules named 'scraper'
        if ispkg or not modname.endswith(".scraper"):
            continue
        try:
            importlib.import_module(modname)
        except Exception:
            # Ignore modules that fail to import during discovery;
            # they won't be included in the registry.
            continue



def discover_scrapers() -> Dict[str, Type[Any]]:
    """Collect all BaseScraper subclasses that define a key."""
    # Ensure scraper subclasses are loaded
    _preload_scraper_modules()

    # Import here to avoid import-time cycles
    from laughtrack.scrapers.base.base_scraper import BaseScraper  # type: ignore

    scrapers: Dict[str, Type[Any]] = {}
    stack = [BaseScraper]
    while stack:
        cls = stack.pop()
        for sub in cls.__subclasses__():
            key = getattr(sub, "key", None)
            if isinstance(key, str) and key:
                scrapers[key] = sub
            stack.append(sub)
    return scrapers


class _LazyRegistry(dict):
    """Lazy-loading registry that discovers scrapers on first access."""

    _loaded: bool = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            discovered = discover_scrapers()
            super().update(discovered)
            self._loaded = True

    # Override common dict methods to trigger load
    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        self._ensure_loaded()
        return super().get(key, default)

    def __getitem__(self, key: Any) -> Any:  # type: ignore[override]
        self._ensure_loaded()
        return super().__getitem__(key)

    def keys(self):  # type: ignore[override]
        self._ensure_loaded()
        return super().keys()

    def items(self):  # type: ignore[override]
        self._ensure_loaded()
        return super().items()

    def __iter__(self):  # type: ignore[override]
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self) -> int:  # type: ignore[override]
        self._ensure_loaded()
        return super().__len__()


# Public registry instance (lazy)
SCRAPERS: Dict[str, Type[Any]] = _LazyRegistry()
