package app.laughtrack.android.feature.search.model

import app.laughtrack.android.core.navigation.AppRoute
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchResultPresentationTest {
    @Test
    fun search_result_preserves_artwork_and_metadata_lines() {
        val result =
            SearchResult(
                title = "Friday Night Laughs",
                subtitle = "Comedy Cellar",
                metadata = listOf("Jun 25, 2026, 8:00 PM", "New York, NY", "Main Room"),
                imageUrl = " https://example.com/show.jpg ",
                route = AppRoute.ShowDetail(42),
            )

        assertTrue(result.hasArtwork)
        assertEquals("https://example.com/show.jpg", result.artworkUrl)
        assertEquals(
            listOf("Comedy Cellar", "Jun 25, 2026, 8:00 PM", "New York, NY", "Main Room"),
            result.displayMetadata,
        )
    }

    @Test
    fun blank_artwork_is_not_treated_as_available() {
        val result =
            SearchResult(
                title = "Jane Comic",
                subtitle = null,
                metadata = emptyList(),
                imageUrl = "  ",
                route = AppRoute.ComedianDetail(7),
            )

        assertFalse(result.hasArtwork)
        assertEquals(null, result.artworkUrl)
        assertEquals(emptyList<String>(), result.displayMetadata)
    }

    @Test
    fun result_count_summary_uses_loaded_and_total_counts() {
        assertEquals("Showing 2 of 14 results", searchResultSummary(loaded = 2, total = 14))
        assertEquals("Showing 1 result", searchResultSummary(loaded = 1, total = 1))
    }

    @Test
    fun podcast_pivot_is_available_for_thumbnail_rows() {
        assertTrue(SearchPivot.PODCASTS.isAvailable)
    }
}
