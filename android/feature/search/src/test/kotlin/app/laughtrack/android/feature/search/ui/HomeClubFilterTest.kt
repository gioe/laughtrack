package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.network.generated.model.HomeClubFilter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Pure-helper tests for the comedian home-club filter control (mirrors iOS HomeClubOption). */
class HomeClubFilterTest {
    private val comedyStore = HomeClubFilter("42", "The Comedy Store", 7)
    private val laughFactory = HomeClubFilter("7", "Laugh Factory", 3)

    @Test
    fun menuOptions_prepend_all_sentinel_and_map_label_with_count() {
        val options = homeClubMenuOptions(listOf(comedyStore, laughFactory))

        assertEquals(3, options.size)
        // Sentinel first: clears the filter.
        assertEquals(HomeClubMenuOption(token = null, label = "All home clubs"), options[0])
        assertEquals(HomeClubMenuOption(token = "42", label = "The Comedy Store (7)"), options[1])
        assertEquals(HomeClubMenuOption(token = "7", label = "Laugh Factory (3)"), options[2])
    }

    @Test
    fun menuOptions_is_just_the_all_sentinel_when_no_filters() {
        val options = homeClubMenuOptions(emptyList())

        assertEquals(1, options.size)
        assertNull(options[0].token)
        assertEquals("All home clubs", options[0].label)
    }

    @Test
    fun triggerLabel_shows_selected_club_name() {
        assertEquals("The Comedy Store", homeClubTriggerLabel("42", listOf(comedyStore, laughFactory)))
    }

    @Test
    fun triggerLabel_falls_back_to_placeholder_for_null_or_unknown_token() {
        assertEquals("Home club", homeClubTriggerLabel(null, listOf(comedyStore, laughFactory)))
        assertEquals("Home club", homeClubTriggerLabel("999", listOf(comedyStore, laughFactory)))
    }

    @Test
    fun reconcile_keeps_a_token_still_offered() {
        assertEquals("42", reconcileHomeClub("42", listOf(comedyStore, laughFactory)))
    }

    @Test
    fun reconcile_clears_a_token_no_longer_offered() {
        assertNull(reconcileHomeClub("42", listOf(laughFactory)))
        // No home-club data at all: any selection clears.
        assertNull(reconcileHomeClub("42", emptyList()))
    }

    @Test
    fun reconcile_leaves_null_untouched() {
        assertNull(reconcileHomeClub(null, listOf(comedyStore, laughFactory)))
    }
}
