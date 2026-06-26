package app.laughtrack.android.feature.search.data

import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ShowSearchArtworkTest {
    @Test
    fun show_search_artwork_prefers_featured_lineup_image_over_relative_show_placeholder() {
        val show =
            show(
                imageUrl = "/placeholders/club-placeholder.svg",
                lineup =
                    listOf(
                        comedian(name = "Opener", imageUrl = "https://example.com/opener.png", showCount = 5),
                        comedian(name = "Headliner", imageUrl = "https://example.com/headliner.png", showCount = 50),
                    ),
            )

        assertEquals("https://example.com/headliner.png", showSearchArtworkUrl(show))
    }

    @Test
    fun show_search_artwork_falls_back_to_absolute_show_image() {
        val show =
            show(
                imageUrl = "https://example.com/show.png",
                lineup = listOf(comedian(name = "No Image", imageUrl = "", showCount = 50)),
            )

        assertEquals("https://example.com/show.png", showSearchArtworkUrl(show))
    }

    @Test
    fun show_search_artwork_ignores_relative_placeholders_when_no_lineup_image_exists() {
        val show = show(imageUrl = "/placeholders/club-placeholder.svg", lineup = emptyList())

        assertNull(showSearchArtworkUrl(show))
    }

    private fun show(
        imageUrl: String,
        lineup: List<ComedianLineup>,
    ): Show =
        Show(
            id = 1,
            clubId = 2,
            date = "2026-06-27T01:15:00.000Z",
            imageUrl = imageUrl,
            clubName = "Comedy Works",
            lineup = lineup,
        )

    private fun comedian(
        name: String,
        imageUrl: String,
        showCount: Int,
    ): ComedianLineup =
        ComedianLineup(
            name = name,
            imageUrl = imageUrl,
            uuid = name.lowercase().replace(" ", "-"),
            id = showCount,
            showCount = showCount,
        )
}
