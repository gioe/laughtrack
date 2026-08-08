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
    fun hero_image_prefers_lineup_art_over_show_and_club_art() {
        val headliner = comedian(1, "Comic")

        assertEquals(headliner.imageUrl, showDetailHeroImageUrl(show(lineup = listOf(headliner))))
    }

    @Test
    fun hero_image_prefers_show_art_when_lineup_art_is_unavailable() {
        assertEquals(
            "https://example.com/show.jpg",
            showDetailHeroImageUrl(show(lineup = emptyList())),
        )
    }

    @Test
    fun hero_image_uses_club_art_as_the_final_fallback() {
        assertEquals(
            "https://example.com/club.jpg",
            showDetailHeroImageUrl(
                show(
                    lineup = listOf(comedian(1, "Comic", imageUrl = " ")),
                    showImageUrl = " ",
                ),
            ),
        )
    }

    @Test
    fun open_mic_uses_show_art_and_hides_lineup_hero() {
        val openMic =
            show(
                name = "Tuesday Open Mic",
                lineup = listOf(comedian(1, "Comic")),
                tags = listOf(Tag(slug = "open-mic", name = "Open Mic")),
            )

        assertNull(showDetailHeroComedian(openMic))
        assertEquals("https://example.com/show.jpg", showDetailHeroImageUrl(openMic))
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
    fun long_show_title_is_preserved_for_multiline_layout() {
        val longTitle = "Sean Patton, Mike Yard, Terry Thomas Jr., Erin Maguire + Surprise Guest"

        assertEquals(
            longTitle,
            showDetailDisplayTitle(show(name = longTitle, lineup = emptyList())),
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
        showImageUrl: String = "https://example.com/show.jpg",
    ) = ShowDetail(
        id = 42,
        date = "2026-07-13T23:00:00Z",
        imageUrl = showImageUrl,
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
        imageUrl: String = "https://example.com/$id.jpg",
    ) = ComedianLineup(
        id = id,
        uuid = "uuid-$id",
        name = name,
        imageUrl = imageUrl,
        showCount = showCount,
        role = role,
    )
}
