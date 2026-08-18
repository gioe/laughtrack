package app.laughtrack.android.feature.detail.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

class PodcastHostPresentationTest {
    @Test
    fun hostCards_allowTwoCenteredNameLinesWithinAWiderCard() {
        assertEquals(100, PODCAST_HOST_CARD_WIDTH_DP)
        assertEquals(2, PODCAST_HOST_NAME_MAX_LINES)
    }

    @Test
    fun source_retainsHorizontallyScrollableHostCards() {
        val source = String(Files.readAllBytes(detailScreenPath("PodcastDetailScreen.kt")))

        assertTrue(source.contains(".horizontalScroll(rememberScrollState())"))
        assertTrue(source.contains(".width(PODCAST_HOST_CARD_WIDTH_DP.dp)"))
        assertTrue(source.contains("maxLines = PODCAST_HOST_NAME_MAX_LINES"))
    }

    private fun detailScreenPath(fileName: String): Path {
        val relativePaths =
            listOf(
                Paths.get(
                    "android/feature/detail/src/main/kotlin",
                    "app/laughtrack/android/feature/detail/ui/$fileName",
                ),
                Paths.get(
                    "feature/detail/src/main/kotlin/app/laughtrack/android/feature/detail/ui/" +
                        fileName,
                ),
            )
        return generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .flatMap { directory -> relativePaths.asSequence().map(directory::resolve) }
            .firstOrNull(Files::isRegularFile)
            ?: error(
                "Unable to locate $fileName from " +
                    Paths.get("").toAbsolutePath(),
            )
    }
}
