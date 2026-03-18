"""ScraperResolver: in-repo auto-discovery of scraper classes.

This service scans the `laughtrack.scrapers.implementations` package for modules
named `scraper` and registers all subclasses of `BaseScraper` that define a
non-empty `key` attribute. It caches the mapping for fast lookups and provides
simple accessors for use cases.

Rationale:
- Avoids a global registry dependency in use cases
- Centralizes discovery & validation (duplicate keys, empty keys)
- Plays nicely with wiring/DI and testing (can be mocked)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Type, Any, List
import importlib
import pkgutil

from laughtrack.foundation.infrastructure.logger.logger import Logger


def _preload_scraper_modules() -> None:
    """Import all leaf modules named 'scraper' under implementations/*.

    This mirrors the package traversal strategy used elsewhere to avoid heavy
    imports of package __init__ modules that may create cycles.
    """
    try:
        import laughtrack.scrapers.implementations as impl_pkg  # type: ignore
    except Exception:
        return

    pkg_paths = getattr(impl_pkg, "__path__", None)
    if not pkg_paths:
        return

    prefix = impl_pkg.__name__ + "."
    for _, modname, ispkg in pkgutil.walk_packages(pkg_paths, prefix):
        # Only import leaf modules named 'scraper' across all subpackages
        if ispkg or not modname.endswith(".scraper"):
            continue
        try:
            importlib.import_module(modname)
        except Exception as e:
            # Skip modules that fail to import during discovery
            Logger.warn(f"Skipping scraper module '{modname}' due to import error: {e}")


@dataclass
class ScraperResolver:
    """Discover and resolve scrapers by key.

    Usage:
        resolver = ScraperResolver()
        scraper_cls = resolver.get("broadway")
        if scraper_cls:
            scraper = scraper_cls(club)
    """

    _registry: Dict[str, Type[Any]] | None = None

    def _ensure_loaded(self) -> None:
        if self._registry is not None:
            return

        # Step 1: Preload modules so subclasses are registered
        _preload_scraper_modules()

        # Step 2: Walk BaseScraper subclass tree
        from laughtrack.scrapers.base.base_scraper import BaseScraper  # type: ignore

        discovered: Dict[str, Type[Any]] = {}
        duplicates: Dict[str, List[str]] = {}

        stack: List[type] = [BaseScraper]
        while stack:
            cls = stack.pop()
            for sub in cls.__subclasses__():
                # Recurse
                stack.append(sub)

                key = getattr(sub, "key", None)
                if not isinstance(key, str) or not key:
                    continue

                # Record and detect duplicates (keep first, warn for others)
                if key not in discovered:
                    discovered[key] = sub
                else:
                    # Track duplicates for logging
                    prev = discovered[key]
                    dup_list = duplicates.setdefault(key, [])
                    dup_list.append(f"{sub.__module__}.{sub.__name__}")
                    # Keep the first discovered class; do not overwrite
                    Logger.warn(
                        f"Duplicate scraper key '{key}': keeping "
                        f"{prev.__module__}.{prev.__name__}, ignoring "
                        f"{sub.__module__}.{sub.__name__}"
                    )

        # Log a summary for visibility
        Logger.info(
            f"Discovered {len(discovered)} scrapers", {"scraper_keys": sorted(discovered.keys())}
        )

        if duplicates:
            Logger.warn(
                "One or more scraper keys had duplicates; first wins",
                {"duplicates": duplicates},
            )

        self._registry = discovered

    def get(self, key: str) -> Optional[Type[Any]]:
        self._ensure_loaded()
        assert self._registry is not None
        return self._registry.get(key)

    def keys(self) -> List[str]:
        self._ensure_loaded()
        assert self._registry is not None
        return list(self._registry.keys())

    def items(self):  # type: ignore[override]
        self._ensure_loaded()
        assert self._registry is not None
        return self._registry.items()
