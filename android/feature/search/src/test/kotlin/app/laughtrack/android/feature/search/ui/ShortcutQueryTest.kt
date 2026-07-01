package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.data.search.SearchSeed
import app.laughtrack.android.core.data.search.SearchShortcut
import app.laughtrack.android.feature.search.model.SearchQuery
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.LocalDate

/** Verifies the Home shortcut chips map to the expected pre-applied Search filters. */
class ShortcutQueryTest {
    private val today = LocalDate.of(2026, 6, 30)
    private val base = SearchQuery(text = "leftover", sort = "popularity")

    @Test
    fun tonight_scopes_to_today_through_tomorrow_earliest_first() {
        val query =
            buildShortcutQuery(
                SearchSeed(SearchShortcut.TONIGHT, zip = "10001", distanceMiles = 25),
                base,
                today,
            )

        assertEquals("2026-06-30", query.from)
        assertEquals("2026-07-01", query.to)
        assertEquals("date_asc", query.sort)
        assertEquals("10001", query.zip)
        assertEquals(25, query.distance)
    }

    @Test
    fun this_week_scopes_to_a_seven_day_window() {
        val query =
            buildShortcutQuery(
                SearchSeed(SearchShortcut.THIS_WEEK, zip = "10001", distanceMiles = 25),
                base,
                today,
            )

        assertEquals("2026-06-30", query.from)
        assertEquals("2026-07-07", query.to)
        assertEquals("date_asc", query.sort)
    }

    @Test
    fun near_me_drops_the_date_window_and_keeps_geo_scope() {
        val query =
            buildShortcutQuery(
                SearchSeed(SearchShortcut.NEAR_ME, zip = "94103", distanceMiles = 50),
                base,
                today,
            )

        assertNull(query.from)
        assertNull(query.to)
        assertEquals("date_asc", query.sort)
        assertEquals("94103", query.zip)
        assertEquals(50, query.distance)
    }
}
