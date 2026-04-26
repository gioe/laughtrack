"""Unit tests for ComedianUtils.normalize_name — noise stripping and existing behaviour.

Uses direct file loading to avoid sys.modules pollution from other test files
that stub ComedianUtils with a MagicMock.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

_SCRAPER_ROOT = Path(__file__).parents[4]  # apps/scraper/


def _load_real_utils() -> type:
    """Load ComedianUtils directly from source, bypassing sys.modules stubs.

    Uses save/restore around sys.modules writes so that the temporary stubs
    needed to load utils.py don't leak into the broader pytest session and
    corrupt other test files that depend on the real module objects.
    """

    _stub_names = [
        "gioe_libs",
        "gioe_libs.string_utils",
        "laughtrack.foundation.infrastructure.logger.logger",
        "laughtrack.foundation.infrastructure.logger",
        "laughtrack.foundation.infrastructure",
        "laughtrack.foundation.utilities.popularity.scorer",
        "laughtrack.foundation.utilities.popularity",
        "laughtrack.foundation.utilities.string",
        "laughtrack.foundation.utilities",
        "laughtrack.foundation",
        "laughtrack.foundation.protocols.database_entity",
        "laughtrack.foundation.protocols",
        "laughtrack.core.entities.comedian.model",
        "laughtrack.core.entities.comedian",
        "laughtrack.core.entities",
    ]

    # Save existing modules so we can restore after loading
    _saved = {name: sys.modules.get(name) for name in _stub_names}

    def _stub(name, as_package=False, **attrs):
        m = ModuleType(name)
        if as_package:
            pkg_path = str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))
            m.__path__ = [pkg_path]
            m.__package__ = name
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        # gioe_libs.string_utils — only remove_parentheses_content is used by normalize_name
        string_utils_stub = MagicMock()
        string_utils_stub.remove_parentheses_content.side_effect = lambda s: s
        _stub("gioe_libs", StringUtils=string_utils_stub)
        _stub("gioe_libs.string_utils", StringUtils=string_utils_stub)

        _stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
        _stub("laughtrack.foundation.infrastructure.logger", Logger=MagicMock())
        _stub("laughtrack.foundation.infrastructure", Logger=MagicMock())
        _stub("laughtrack.foundation.utilities.popularity.scorer", PopularityScorer=MagicMock())
        _stub("laughtrack.foundation.utilities.popularity", PopularityScorer=MagicMock())
        _stub("laughtrack.foundation.utilities.string", StringUtils=string_utils_stub)
        _stub("laughtrack.foundation.utilities", StringUtils=string_utils_stub)
        _stub("laughtrack.foundation", as_package=True, DatabaseEntity=object)
        _stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
        _stub("laughtrack.foundation.protocols", DatabaseEntity=object)
        _stub("laughtrack.core.entities.comedian.model", Comedian=MagicMock())
        _stub("laughtrack.core.entities.comedian", Comedian=MagicMock())
        _stub("laughtrack.core.entities", Comedian=MagicMock())

        path = _SCRAPER_ROOT / "src/laughtrack/utilities/domain/comedian/utils.py"
        spec = importlib.util.spec_from_file_location("_comedian_utils_real", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.ComedianUtils
    finally:
        # Restore pre-existing modules; remove any stubs that weren't there before
        for name, original in _saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


ComedianUtils = _load_real_utils()


class TestNormalizeName:
    # --- colon subtitle stripping ---

    def test_strips_subtitle_after_colon(self):
        assert ComedianUtils.normalize_name("Adam Carolla: All New Material") == "Adam Carolla"

    def test_strips_subtitle_after_colon_allcaps(self):
        assert ComedianUtils.normalize_name("ADAM CAROLLA: ALL NEW MATERIAL") == "Adam Carolla"

    def test_strips_subtitle_tour_name(self):
        assert ComedianUtils.normalize_name("Craig Ferguson: Pants On Fire") == "Craig Ferguson"

    def test_no_colon_unchanged(self):
        assert ComedianUtils.normalize_name("Adam Carolla") == "Adam Carolla"

    def test_multiple_colons_keeps_only_before_first(self):
        assert ComedianUtils.normalize_name("Special Event: IMHO: Live!") == "Special Event"

    def test_colon_with_extra_whitespace(self):
        assert ComedianUtils.normalize_name("Jeff Arcuri :  Fresh Cut  ") == "Jeff Arcuri"

    # --- leading role prefix stripping ---

    def test_strips_comedian_prefix(self):
        assert ComedianUtils.normalize_name("Comedian Adam Hunter") == "Adam Hunter"

    def test_strips_comedian_prefix_case_insensitive(self):
        assert ComedianUtils.normalize_name("COMEDIAN ADAM HUNTER") == "Adam Hunter"

    def test_strips_comedy_magician_prefix(self):
        assert ComedianUtils.normalize_name("Comedy Magician Jack Grady") == "Jack Grady"

    def test_strips_comedian_prefix_and_live_in_suffix(self):
        assert ComedianUtils.normalize_name(
            "Comedian Adam Hunter Live in Naples, Florida!"
        ) == "Adam Hunter"

    # --- trailing noise suffix stripping ---

    def test_strips_dash_special_event(self):
        assert ComedianUtils.normalize_name("Kevin McCaffrey - Special Event") == "Kevin McCaffrey"

    def test_strips_dash_special_event_with_dates(self):
        assert ComedianUtils.normalize_name(
            "Adam Ferrara - Special Event - 9/18 - 9/19"
        ) == "Adam Ferrara"

    def test_strips_dash_live(self):
        assert ComedianUtils.normalize_name("Landon Talks - Live") == "Landon Talks"

    def test_strips_dash_live_allcaps(self):
        assert ComedianUtils.normalize_name("Scuffed Realtor - LIVE") == "Scuffed Realtor"

    def test_strips_live_in_city(self):
        assert ComedianUtils.normalize_name(
            "Comedian Brad Upton Live in Naples, Florida!"
        ) == "Brad Upton"

    def test_strips_live_in_city_no_comedian_prefix(self):
        assert ComedianUtils.normalize_name(
            "Davide De Pierro Live in Naples, Florida!"
        ) == "Davide De Pierro"

    def test_strips_from_quoted_show(self):
        assert ComedianUtils.normalize_name(
            'Andy Huggins From "America\'s Got Talent"'
        ) == "Andy Huggins"

    def test_strips_from_allcaps_abbreviation(self):
        assert ComedianUtils.normalize_name("Michael Longfellow From SNL") == "Michael Longfellow"

    # --- existing behaviour preserved ---

    def test_trims_whitespace(self):
        assert ComedianUtils.normalize_name("  John Doe  ") == "John Doe"

    def test_title_cases_all_upper(self):
        assert ComedianUtils.normalize_name("JOHN DOE") == "John Doe"

    def test_title_cases_all_lower(self):
        assert ComedianUtils.normalize_name("john doe") == "John Doe"

    def test_mixed_case_unchanged(self):
        assert ComedianUtils.normalize_name("John Doe") == "John Doe"

    def test_empty_string(self):
        assert ComedianUtils.normalize_name("") == ""

    def test_hyphenated_name_unchanged(self):
        assert ComedianUtils.normalize_name("Jo-Anne Smith") == "Jo-Anne Smith"
