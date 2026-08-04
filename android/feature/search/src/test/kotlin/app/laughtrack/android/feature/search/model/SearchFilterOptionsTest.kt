package app.laughtrack.android.feature.search.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Locks the per-pivot sort vocabulary and defaults to the server keys shared with
 * iOS (SearchOptions.swift) and web, so a wrong-key regression fails here rather
 * than silently returning unsorted results at runtime.
 */
class SearchFilterOptionsTest {
    @Test
    fun each_pivot_default_sort_matches_the_server_default_key() {
        assertEquals("date_asc", SearchSort.defaultFor(SearchPivot.SHOWS))
        assertEquals("popularity_desc", SearchSort.defaultFor(SearchPivot.COMEDIANS))
        assertEquals("total_shows_desc", SearchSort.defaultFor(SearchPivot.CLUBS))
        assertEquals("show_count_desc", SearchSort.defaultFor(SearchPivot.PODCASTS))
    }

    @Test
    fun show_sort_options_expose_earliest_latest_and_price_axes() {
        val values = SearchSort.optionsFor(SearchPivot.SHOWS).map { it.apiValue }
        assertEquals(listOf("date_asc", "date_desc", "price_asc", "price_desc"), values)
    }

    @Test
    fun label_resolves_selected_value_and_falls_back_to_pivot_default() {
        assertEquals("Latest", SearchSort.labelFor(SearchPivot.SHOWS, "date_desc"))
        // Unknown/null value falls back to the leading (default) option's label.
        assertEquals("Earliest", SearchSort.labelFor(SearchPivot.SHOWS, null))
        assertEquals("Earliest", SearchSort.labelFor(SearchPivot.SHOWS, "bogus_key"))
    }

    @Test
    fun podcasts_do_not_support_tag_filters_but_other_pivots_do() {
        assertFalse(SearchPivot.PODCASTS.supportsTagFilters)
        assertTrue(SearchPivot.SHOWS.supportsTagFilters)
        assertTrue(SearchPivot.COMEDIANS.supportsTagFilters)
        assertTrue(SearchPivot.CLUBS.supportsTagFilters)
    }

    @Test
    fun distance_options_are_the_four_iOS_radii_with_city_default() {
        assertEquals(listOf(10, 25, 50, 100), DISTANCE_OPTIONS)
        assertEquals(25, DEFAULT_DISTANCE_MILES)
    }

    @Test
    fun show_explorer_options_use_canonical_api_values() {
        assertEquals(listOf("standup", "improv", "open_mic"), ShowFormatOption.entries.map { it.slug })
        assertEquals(listOf(null, 20, 40, 60, 100), ShowMaximumPriceOption.entries.map { it.apiValue })
        assertEquals(
            listOf(ShowResultsPresentation.AGENDA, ShowResultsPresentation.CALENDAR),
            ShowResultsPresentation.entries,
        )
    }
}
