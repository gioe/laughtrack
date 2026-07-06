package app.laughtrack.android.feature.search.ui

import org.junit.Assert.assertEquals
import org.junit.Test

/** Verifies the date pill's label reflects the selected window (or "Any date" when unset). */
class DateRangeLabelTest {
    @Test
    fun no_bounds_reads_any_date() {
        assertEquals("Any date", dateRangeLabel(null, null))
    }

    @Test
    fun equal_bounds_render_as_a_single_day() {
        assertEquals("Jul 4", dateRangeLabel("2026-07-04", "2026-07-04"))
    }

    @Test
    fun distinct_bounds_render_as_a_range() {
        assertEquals("Jul 4 - Jul 11", dateRangeLabel("2026-07-04", "2026-07-11"))
    }

    @Test
    fun open_ended_bounds_read_from_or_until() {
        assertEquals("From Jul 4", dateRangeLabel("2026-07-04", null))
        assertEquals("Until Jul 11", dateRangeLabel(null, "2026-07-11"))
    }
}
