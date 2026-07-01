package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Pure-helper tests for the comedian home-city filter control (mirrors iOS HomeCityOption). */
class HomeCityFilterTest {
    private val chicago = HomeCityFilter("Chicago|IL", "Chicago, IL", 7)
    private val austin = HomeCityFilter("Austin|TX", "Austin, TX", 3)

    @Test
    fun menuOptions_prepend_all_sentinel_and_map_label_with_count() {
        val options = homeCityMenuOptions(listOf(chicago, austin))

        assertEquals(3, options.size)
        // Sentinel first: clears the filter.
        assertEquals(HomeCityMenuOption(token = null, label = "All home cities"), options[0])
        assertEquals(HomeCityMenuOption(token = "Chicago|IL", label = "Chicago, IL (7)"), options[1])
        assertEquals(HomeCityMenuOption(token = "Austin|TX", label = "Austin, TX (3)"), options[2])
    }

    @Test
    fun menuOptions_is_just_the_all_sentinel_when_no_filters() {
        val options = homeCityMenuOptions(emptyList())

        assertEquals(1, options.size)
        assertNull(options[0].token)
        assertEquals("All home cities", options[0].label)
    }

    @Test
    fun triggerLabel_shows_selected_city_name() {
        assertEquals("Chicago, IL", homeCityTriggerLabel("Chicago|IL", listOf(chicago, austin)))
    }

    @Test
    fun triggerLabel_falls_back_to_placeholder_for_null_or_unknown_token() {
        assertEquals("Home city", homeCityTriggerLabel(null, listOf(chicago, austin)))
        assertEquals("Home city", homeCityTriggerLabel("Nowhere|ZZ", listOf(chicago, austin)))
    }

    @Test
    fun reconcile_keeps_a_token_still_offered() {
        assertEquals("Chicago|IL", reconcileHomeCity("Chicago|IL", listOf(chicago, austin)))
    }

    @Test
    fun reconcile_clears_a_token_no_longer_offered() {
        assertNull(reconcileHomeCity("Chicago|IL", listOf(austin)))
        // No home-location data at all: any selection clears.
        assertNull(reconcileHomeCity("Chicago|IL", emptyList()))
    }

    @Test
    fun reconcile_leaves_null_untouched() {
        assertNull(reconcileHomeCity(null, listOf(chicago, austin)))
    }
}
