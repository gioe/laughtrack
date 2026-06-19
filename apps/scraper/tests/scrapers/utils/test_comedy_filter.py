"""Unit tests for the shared opt-in comedy filter (TASK-3010 / TASK-3011).

Covers the three keep-signals (keyword, allowlist, known-comedian-above-floor),
the popularity floor that drops false positives, and the metadata config readers.
Handlers are injected fakes, so no DB is touched.
"""

from laughtrack.scrapers.utils.comedy_filter import (
    DEFAULT_MIN_COMEDIAN_POPULARITY,
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)


class _Comedian:
    def __init__(self, name):
        self.name = name


class _FakeLineupHandler:
    """Returns credible comedian name matches keyed by show title."""

    def __init__(self, matches):
        self._matches = matches

    def get_comedians_from_show_names(self, show_names):
        wanted = {t[0] for t in show_names}
        return {
            title: [_Comedian(n) for n in names]
            for title, names in self._matches.items()
            if title in wanted
        }


class _FakeComedianHandler:
    def __init__(self, popularity):
        self._popularity = popularity

    def get_stored_popularity_by_names(self, names):
        return {n: self._popularity[n] for n in names if n in self._popularity}


class _ExplodingHandler:
    """Asserts the DB path is never reached (cheap signals should short-circuit)."""

    def get_comedians_from_show_names(self, show_names):  # pragma: no cover
        raise AssertionError("name-match lookup should not run for keyword/allowlist hits")

    def get_stored_popularity_by_names(self, names):  # pragma: no cover
        raise AssertionError("popularity lookup should not run")


class TestKeywordSignal:
    def test_keeps_keyword_titles_without_db(self):
        # "Cutthroat Improv" / "Stand-Up" carry comedy keywords -> kept via the
        # cheap path; the exploding handler proves the DB path isn't reached.
        result = select_comedy_titles(
            ["Cutthroat Improv", "FREE Stand-Up Comedy Night"],
            lineup_handler=_ExplodingHandler(),
            comedian_handler=_ExplodingHandler(),
        )
        assert result == {"Cutthroat Improv", "FREE Stand-Up Comedy Night"}

    def test_keyword_in_description_keeps_title(self):
        result = select_comedy_titles(
            ["Friday Night Live"],
            lineup_handler=_FakeLineupHandler({}),
            comedian_handler=_FakeComedianHandler({}),
            descriptions={"Friday Night Live": "An evening of stand-up comedy"},
        )
        assert result == {"Friday Night Live"}

    def test_drops_non_comedy_without_match(self):
        # Dance classes: no keyword, no allowlist, no comedian match -> dropped.
        result = select_comedy_titles(
            ["Bachata 101 + Practice Party", "Salsa Sundays"],
            lineup_handler=_FakeLineupHandler({}),
            comedian_handler=_FakeComedianHandler({}),
        )
        assert result == set()


class TestKnownComedianSignal:
    def test_keeps_name_only_touring_act_above_floor(self):
        # "Sean Patton" has no comedy keyword; kept via the known-comedian path.
        lineup = _FakeLineupHandler({"Sean Patton": ["Sean Patton"]})
        comedian = _FakeComedianHandler({"Sean Patton": 0.47})
        result = select_comedy_titles(
            ["Sean Patton"],
            lineup_handler=lineup,
            comedian_handler=comedian,
            min_popularity=0.30,
        )
        assert result == {"Sean Patton"}

    def test_drops_below_floor_false_positive(self):
        lineup = _FakeLineupHandler({"The Nutcracker": ["The Nutcracker"]})
        comedian = _FakeComedianHandler({"The Nutcracker": 0.18})
        result = select_comedy_titles(
            ["The Nutcracker"],
            lineup_handler=lineup,
            comedian_handler=comedian,
            min_popularity=0.30,
        )
        assert result == set()

    def test_mixed_calendar_keeps_only_comedy(self):
        titles = ["Cutthroat Improv", "Guy Branum", "Intro to Ballroom Dance"]
        lineup = _FakeLineupHandler({"Guy Branum": ["Guy Branum"]})
        comedian = _FakeComedianHandler({"Guy Branum": 0.51})
        result = select_comedy_titles(
            titles, lineup_handler=lineup, comedian_handler=comedian
        )
        assert result == {"Cutthroat Improv", "Guy Branum"}


class TestAllowlist:
    def test_allowlist_force_includes_unmatched_title(self):
        result = select_comedy_titles(
            ["Variety Hour Spectacular", "Some Concert"],
            lineup_handler=_FakeLineupHandler({}),
            comedian_handler=_FakeComedianHandler({}),
            allowlist=["variety hour"],
        )
        assert result == {"Variety Hour Spectacular"}

    def test_empty_inputs(self):
        assert (
            select_comedy_titles(
                [], lineup_handler=_FakeLineupHandler({}),
                comedian_handler=_FakeComedianHandler({}),
            )
            == set()
        )


class TestMetadataReaders:
    def test_is_enabled(self):
        assert is_comedy_filter_enabled({"comedy_filter": True}) is True
        assert is_comedy_filter_enabled({"comedy_filter": False}) is False
        assert is_comedy_filter_enabled({}) is False
        assert is_comedy_filter_enabled(None) is False

    def test_resolve_min_popularity(self):
        assert resolve_min_popularity({"min_comedian_popularity": 0.5}) == 0.5
        assert resolve_min_popularity({}) == DEFAULT_MIN_COMEDIAN_POPULARITY
        assert resolve_min_popularity({"min_comedian_popularity": "bad"}) == DEFAULT_MIN_COMEDIAN_POPULARITY
        assert resolve_min_popularity(None) == DEFAULT_MIN_COMEDIAN_POPULARITY

    def test_resolve_allowlist(self):
        assert resolve_allowlist({"comedy_title_allowlist": ["a", "b"]}) == ["a", "b"]
        assert resolve_allowlist({"comedy_title_allowlist": "single"}) == ["single"]
        assert resolve_allowlist({}) == []
        assert resolve_allowlist(None) == []
        assert resolve_allowlist({"comedy_title_allowlist": ["", "  ", "x"]}) == ["x"]
