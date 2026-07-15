package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.ShowDetail
import app.laughtrack.android.core.network.generated.model.ShowDetailClub
import app.laughtrack.android.core.network.generated.model.ShowDetailCta
import app.laughtrack.android.core.network.generated.model.Tag
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ShowDetailPresentationTest {
    @Test
    fun hero_comedian_preserves_lineup_order_when_scores_tie() {
        val cansu = comedian(1, "Cansu Karabiyik")
        val alex = comedian(2, "Alex Pavone")

        assertEquals(cansu, showDetailHeroComedian(show(lineup = listOf(cansu, alex))))
    }

    @Test
    fun hero_comedian_uses_api_lineup_order_even_when_later_comedian_is_more_popular() {
        val popular = comedian(1, "Popular", showCount = 2)
        val prolific = comedian(2, "Prolific", showCount = 100)

        assertEquals(prolific, showDetailHeroComedian(show(lineup = listOf(prolific, popular))))
    }

    @Test
    fun open_mic_uses_club_art_and_hides_lineup_hero() {
        val openMic =
            show(
                name = "Tuesday Open Mic",
                lineup = listOf(comedian(1, "Comic")),
                tags = listOf(Tag(slug = "open-mic", name = "Open Mic")),
            )

        assertNull(showDetailHeroComedian(openMic))
        assertEquals("https://example.com/club.jpg", showDetailHeroImageUrl(openMic))
    }

    @Test
    fun show_title_matches_ios_performer_and_lineup_rules() {
        val solo = comedian(1, "Vanessa Jackson")

        assertEquals(
            "Vanessa Jackson Headlines",
            showDetailDisplayTitle(show(name = "Vanessa Jackson", lineup = listOf(solo))),
        )
        assertEquals(
            "Comedy Show at Comedy Room",
            showDetailDisplayTitle(show(name = "John Smith", lineup = emptyList())),
        )
        assertEquals(
            "Backroom Comedy",
            showDetailDisplayTitle(show(name = "Backroom Comedy", lineup = emptyList())),
        )
    }

    @Test
    fun lineup_role_badge_trims_and_omits_blank_roles() {
        assertEquals("Headliner", showLineupRoleBadge(comedian(1, "Comic", role = " Headliner ")))
        assertNull(showLineupRoleBadge(comedian(2, "Comic", role = " ")))
    }

    private fun show(
        name: String = "Backroom Comedy",
        lineup: List<ComedianLineup>,
        tags: List<Tag>? = null,
    ) = ShowDetail(
        id = 42,
        date = "2026-07-13T23:00:00Z",
        imageUrl = "https://example.com/show.jpg",
        showPageUrl = "https://example.com/show/42",
        club = ShowDetailClub(id = 7, name = "Comedy Room", imageUrl = "https://example.com/club.jpg"),
        cta = ShowDetailCta(label = "Buy tickets", isSoldOut = false),
        name = name,
        lineup = lineup,
        tags = tags,
    )

    private fun comedian(
        id: Int,
        name: String,
        showCount: Int? = null,
        role: String? = null,
    ) = ComedianLineup(
        id = id,
        uuid = "uuid-$id",
        name = name,
        imageUrl = "https://example.com/$id.jpg",
        showCount = showCount,
        role = role,
    )
}
