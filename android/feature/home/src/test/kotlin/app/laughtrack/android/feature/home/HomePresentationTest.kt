package app.laughtrack.android.feature.home

import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import org.junit.Assert.assertEquals
import org.junit.Test

class HomePresentationTest {
    @Test
    fun preferred_headliner_overrides_normal_show_count_ranking() {
        val usualHeadliner = comedian(id = 1, name = "Usual Headliner", showCount = 100)
        val visitingComedian = comedian(id = 2, name = "Visiting Comedian", showCount = 2)
        val show = show(lineup = listOf(usualHeadliner, visitingComedian))

        assertEquals("Visiting Comedian", showHeadliner(show, preferredComedianId = 2)?.name)
    }

    @Test
    fun preferred_canonical_headliner_resolves_through_alias() {
        val canonical = comedian(id = 2, name = "Canonical Visitor", showCount = 2)
        val alias = comedian(id = 3, name = "Visitor Alias", showCount = 2, parent = canonical)

        assertEquals("Canonical Visitor", showHeadliner(show(listOf(alias)), preferredComedianId = 2)?.name)
    }

    @Test
    fun featured_show_artwork_uses_the_preferred_headliner() {
        val usualHeadliner = comedian(id = 1, name = "Usual Headliner", showCount = 100)
        val visitingComedian = comedian(id = 2, name = "Visiting Comedian", showCount = 2)
        val show = show(lineup = listOf(usualHeadliner, visitingComedian))

        assertEquals("Visiting Comedian", heroArtworkCaption(show, preferredComedianId = 2))
        assertEquals("https://example.com/2.jpg", heroArtworkUrl(show, preferredComedianId = 2))
    }

    @Test
    fun featured_show_date_time_includes_the_venue_date_and_timestamp() {
        val show =
            Show(
                id = 10,
                clubId = 20,
                date = "2026-08-08T20:00:00-04:00",
                imageUrl = "",
                name = "Late show",
                timezone = "America/New_York",
            )

        assertEquals("SAT, AUG 8 • 8:00 PM EDT", formatShowDateTime(show))
    }

    private fun show(lineup: List<ComedianLineup>) =
        Show(
            id = 10,
            clubId = 20,
            date = "2026-08-08T20:00:00-04:00",
            imageUrl = "",
            name = "Late show",
            lineup = lineup,
        )

    private fun comedian(
        id: Int,
        name: String,
        showCount: Int,
        parent: ComedianLineup? = null,
    ) = ComedianLineup(
        id = id,
        uuid = "comedian-$id",
        name = name,
        imageUrl = "https://example.com/$id.jpg",
        showCount = showCount,
        parentComedian = parent,
    )
}
