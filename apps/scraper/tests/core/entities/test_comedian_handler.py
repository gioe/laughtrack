"""
Unit tests for ComedianHandler.insert_comedians.

Verifies that the insert-only (DO NOTHING on conflict) contract is upheld:
name-only stubs created during lineup extraction must never overwrite
existing comedian data.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Load source modules directly from file, bypassing package __init__.py
# chains that require a live DB environment.
# ---------------------------------------------------------------------------
_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/


def _load_module(rel_path: str, module_name: str):
    """Import a single .py file as a module without triggering __init__.py chains."""
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    # Stub psycopg2 if needed before execution
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict  # type: ignore[attr-defined]
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object  # type: ignore[attr-defined]
        psycopg2.extras = extras  # type: ignore[attr-defined]
        psycopg2.extensions = extensions  # type: ignore[attr-defined]
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


# Stub foundation modules that comedian model needs
def _stub(name: str, **attrs):
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure", Logger=MagicMock())
_stub("laughtrack.foundation.utilities.popularity.scorer", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.popularity", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.string", StringUtils=MagicMock())
_stub("laughtrack.foundation.utilities", StringUtils=MagicMock())
_stub("laughtrack.foundation", DatabaseEntity=object)
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain", ComedianUtils=MagicMock())
_stub("laughtrack.utilities", ComedianUtils=MagicMock())

# Load comedian model directly (bypasses comedian __init__.py which pulls in handler)
_comedian_model_mod = _load_module("src/laughtrack/core/entities/comedian/model.py",
                                   "laughtrack.core.entities.comedian.model_direct")
Comedian = _comedian_model_mod.Comedian

# Load ComedianQueries directly (no deps)
_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")
ComedianQueries = _comedian_queries_mod.ComedianQueries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid_for(name: str) -> str:
    """Replicate the deterministic UUID logic for test assertions."""
    import hashlib
    normalized = name.lower().strip()
    return str(hashlib.md5(normalized.encode()).hexdigest())


def _make_stub(name: str) -> Comedian:
    """Create a name-only comedian stub as produced by lineup extraction."""
    c = Comedian.__new__(Comedian)
    # Set defaults matching the dataclass definition
    c.name = name
    c.uuid = None
    c.sold_out_shows = 0
    c.total_shows = 0
    c.instagram_followers = None
    c.tiktok_followers = None
    c.youtube_followers = None
    c.instagram_account = None
    c.tiktok_account = None
    c.youtube_account = None
    c.website = None
    c.linktree = None
    c.parent_comedian_id = None
    c.recency_score = 0.0
    return c


def _make_full_comedian(name: str) -> Comedian:
    """Create a comedian with social/follower data."""
    c = _make_stub(name)
    c.instagram_followers = 50_000
    c.tiktok_followers = 120_000
    c.sold_out_shows = 3
    c.total_shows = 10
    return c


# ---------------------------------------------------------------------------
# SQL-level contract
# ---------------------------------------------------------------------------

class TestBatchAddComediansSql:
    def test_uses_do_nothing_on_conflict(self):
        """Regression guard: BATCH_ADD_COMEDIANS must use DO NOTHING, not DO UPDATE."""
        sql = ComedianQueries.BATCH_ADD_COMEDIANS.upper()
        assert "DO NOTHING" in sql, "Expected ON CONFLICT DO NOTHING in BATCH_ADD_COMEDIANS"
        assert "DO UPDATE" not in sql, "DO UPDATE would overwrite existing comedian data"

    def test_inserts_only_base_fields(self):
        """The INSERT column list must not include social/follower fields."""
        import re
        match = re.search(r"INSERT INTO comedians\s*\(([^)]+)\)", ComedianQueries.BATCH_ADD_COMEDIANS, re.I)
        assert match, "Could not find INSERT column list"
        cols = [c.strip().lower() for c in match.group(1).split(",")]
        for social_field in ("instagram_followers", "tiktok_followers", "youtube_followers",
                             "instagram_account", "tiktok_account", "youtube_account"):
            assert social_field not in cols, (
                f"Social field '{social_field}' must not be in INSERT to avoid overwriting existing data"
            )


# ---------------------------------------------------------------------------
# Model-level contract
# ---------------------------------------------------------------------------

class TestComedianInsertTuple:
    def test_to_insert_tuple_excludes_social_fields(self):
        """to_insert_tuple() must only include (uuid, name, sold_out_shows, total_shows)."""
        comedian = _make_full_comedian("Amy Schumer")
        comedian.uuid = "test-uuid-123"
        t = comedian.to_insert_tuple()
        assert len(t) == 4
        assert t[0] == comedian.uuid
        assert t[1] == comedian.name
        assert t[2] == comedian.sold_out_shows
        assert t[3] == comedian.total_shows

    def test_stub_to_insert_tuple_has_zero_show_counts(self):
        """Stubs from lineup extraction have 0 show counts, so any additive update would be a no-op."""
        stub = _make_stub("Chris Rock")
        stub.uuid = "some-uuid"
        t = stub.to_insert_tuple()
        assert t[2] == 0, "sold_out_shows should be 0 for name-only stubs"
        assert t[3] == 0, "total_shows should be 0 for name-only stubs"

    def test_social_fields_not_in_insert_tuple(self):
        """Confirm social fields present on the model are excluded from to_insert_tuple."""
        comedian = _make_full_comedian("Dave Chappelle")
        comedian.uuid = "uuid-456"
        t = comedian.to_insert_tuple()
        # instagram_followers=50000 must NOT appear in the tuple
        assert comedian.instagram_followers not in t
        assert comedian.tiktok_followers not in t
