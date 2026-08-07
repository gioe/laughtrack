package app.laughtrack.android.feature.home

import app.laughtrack.android.core.analytics.AnalyticsEvents
import org.junit.Assert.assertEquals
import org.junit.Test

class HomeDiscoverRailAnalyticsTest {
    @Test
    fun selection_includes_rail_key_policy_version_and_one_based_item_rank() {
        val event =
            homeDiscoverRailSelectedEvent(
                HomeDiscoverRailAttribution(
                    railKey = "starting_to_buzz",
                    policyVersion = 7,
                    rank = 4,
                ),
            )

        assertEquals(AnalyticsEvents.Discover.RAIL_SELECTED, event.name)
        assertEquals(
            mapOf(
                AnalyticsEvents.Discover.Param.RAIL_KEY to "starting_to_buzz",
                AnalyticsEvents.Discover.Param.POLICY_VERSION to 7,
                AnalyticsEvents.Discover.Param.RANK to 4,
            ),
            event.params,
        )
    }
}
