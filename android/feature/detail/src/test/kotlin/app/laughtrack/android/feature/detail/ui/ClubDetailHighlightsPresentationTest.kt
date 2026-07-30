package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.ClubHighlights
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

class ClubDetailHighlightsPresentationTest {
    @Test
    fun tonight_takes_precedence_over_next_show() {
        val featured =
            clubFeaturedShow(
                highlights(tonight = listOf(show(1)), next = show(2)),
            )

        assertEquals("Tonight", featured?.eyebrow)
        assertEquals(1, featured?.show?.id)
    }

    @Test
    fun next_up_is_the_fallback_when_tonight_is_empty() {
        val featured = clubFeaturedShow(highlights(next = show(2)))

        assertEquals("Next up", featured?.eyebrow)
        assertEquals(2, featured?.show?.id)
    }

    @Test
    fun show_section_is_omitted_when_neither_candidate_exists() {
        assertNull(clubFeaturedShow(highlights()))
    }

    @Test
    fun frequent_performers_are_exposed_only_when_present() {
        assertTrue(clubFrequentPerformers(highlights()).isEmpty())

        val performer = performer(8, "Aparna Nancherla")
        assertEquals(listOf(performer), clubFrequentPerformers(highlights(performers = listOf(performer))))
    }

    @Test
    fun source_wires_typed_navigation_and_actionable_semantics() {
        val source = String(Files.readAllBytes(clubDetailScreenPath()))

        assertTrue(source.contains("AppRoute.ShowDetail(featured.show.id)"))
        assertTrue(source.contains("AppRoute.ComedianDetail(it.id)"))
        assertTrue(source.contains("testTag(CLUB_HIGHLIGHT_SECTION_TEST_TAG)"))
        assertTrue(source.contains("testTag(CLUB_FREQUENT_PERFORMERS_SECTION_TEST_TAG)"))
        assertTrue(source.contains("contentDescription = \"Open \${show.name ?: \"show\"}\""))
        assertTrue(source.contains("contentDescription = \"Open \${performer.name}\""))
        assertTrue(source.contains("clickable(role = Role.Button)"))
    }

    private fun highlights(
        tonight: List<Show> = emptyList(),
        next: Show? = null,
        performers: List<ComedianListItem> = emptyList(),
    ) = ClubHighlights(
        tonightShows = tonight,
        nextShow = next,
        frequentPerformers = performers,
    )

    private fun show(id: Int) =
        Show(
            id = id,
            clubId = 42,
            date = "2026-07-30T20:00:00-04:00",
            imageUrl = "https://example.com/show-$id.jpg",
            name = "Show $id",
        )

    private fun performer(
        id: Int,
        name: String,
    ) = ComedianListItem(
        id = id,
        uuid = "uuid-$id",
        name = name,
        imageUrl = "https://example.com/comedian-$id.jpg",
        socialData = SocialData(id),
        showCount = 12,
    )

    private fun clubDetailScreenPath(): Path {
        val relativePaths =
            listOf(
                Paths.get(
                    "android/feature/detail/src/main/kotlin",
                    "app/laughtrack/android/feature/detail/ui/ClubDetailScreen.kt",
                ),
                Paths.get(
                    "feature/detail/src/main/kotlin/app/laughtrack/android/feature/detail/ui/ClubDetailScreen.kt",
                ),
            )
        return generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .flatMap { directory -> relativePaths.asSequence().map(directory::resolve) }
            .firstOrNull(Files::isRegularFile)
            ?: error("Unable to locate ClubDetailScreen.kt from ${Paths.get("").toAbsolutePath()}")
    }
}
