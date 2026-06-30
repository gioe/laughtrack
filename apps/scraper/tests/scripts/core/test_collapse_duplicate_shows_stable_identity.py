"""Unit tests for the collapse_duplicate_shows_stable_identity backfill (TASK-3491).

The script's heavy lifting is a temp-table + window-function SQL pass that is not
faithfully reproducible in a fake cursor, so these tests cover the pure helper
(`_club_filter`) behaviorally and assert the structure of the SQL that carries
the TASK-3491 must-fix hardening: the scoped/anchored sid grouping, the
sent_notifications intra-group dedup, and the commit-then-log ordering.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
for _p in (str(_repo_root / "src"), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import collapse_duplicate_shows_stable_identity as mod  # noqa: E402


class TestClubFilter:
    def test_no_club_is_vacuous_true_with_no_params(self):
        assert mod._club_filter(None) == ("TRUE", ())

    def test_club_scopes_unaliased_with_param(self):
        assert mod._club_filter(53) == ("club_id = %s", (53,))

    def test_club_scopes_with_explicit_alias(self):
        # The alias is applied directly — no brittle string .replace at the call site.
        assert mod._club_filter(53, alias="s") == ("s.club_id = %s", (53,))

    def test_alias_ignored_when_club_is_none(self):
        assert mod._club_filter(None, alias="s") == ("TRUE", ())


class TestSidGroupingScoped:
    """Criterion 11483: sid grouping scoped to seatengine_classic/NULL + anchored regex."""

    def test_uses_delimiter_anchored_regex(self):
        assert mod._SEATENGINE_SHOW_ID_RE == "/shows/([0-9]+)(?:[/?#]|$)"
        assert mod._SEATENGINE_SHOW_ID_RE in mod._GROUP_KEY_SQL

    def test_sid_branch_scoped_to_seatengine_classic_or_null(self):
        key_sql = " ".join(mod._GROUP_KEY_SQL.split()).lower()
        assert "last_scraped_by = 'seatengine_classic' or last_scraped_by is null" in key_sql

    def test_unscoped_bare_regex_not_used(self):
        # The pre-fix bare regex (no delimiter anchor) must be gone.
        assert "from '/shows/([0-9]+)')" not in mod._GROUP_KEY_SQL


class TestSentNotificationsDedup:
    """Criterion 11484: intra-group dedup before the repoint UPDATE."""

    def test_repoint_dedupes_intra_group_on_unique_key(self):
        src = " ".join(inspect.getsource(mod._repoint_children_and_delete).split()).lower()
        # A ROW_NUMBER pass partitioned by the sent_notifications unique-key tuple
        # keeps one row per (survivor, user, comedian, type) among the old rows.
        assert "row_number() over" in src
        assert "partition by m.new_show_id, s2.user_id, s2.comedian_id, s2.notification_type" in src
        assert "dups.rn > 1" in src
        # The repoint UPDATE still runs after the dedup.
        assert "update sent_notifications sn set show_id = m.new_show_id" in src


class TestRecoveryLogAfterCommit:
    """Criterion 11485: recovery log is written only after the transaction commits."""

    def test_log_write_is_outside_the_transaction_block(self):
        src = inspect.getsource(mod.run)
        # The log write is guarded at function-body indent (4 spaces) AFTER the
        # `with get_transaction()` block has exited and committed — not at the
        # 12-space indent inside the transaction.
        assert "\n    if apply:\n        _write_recovery_log(payload)" in src
        assert src.index("with get_transaction()") < src.index("_write_recovery_log(payload)")
        # The rollback (dry-run) stays inside the transaction.
        assert "\n                conn.rollback()" in src


class TestNoBrittleAliasing:
    """Criterion 11485: explicit alias param replaced the string .replace hack."""

    def test_no_string_replace_of_club_id(self):
        src = inspect.getsource(mod)
        assert ".replace('club_id'" not in src
        assert '.replace("club_id"' not in src
