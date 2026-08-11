package app.laughtrack.android.feature.home

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

class TonightCarouselTest {
    @Test
    fun selectedIndexStaysWithinCarouselBounds() {
        assertEquals(0, tonightSelectedIndex(firstVisibleItemIndex = -1, showCount = 0))
        assertEquals(0, tonightSelectedIndex(firstVisibleItemIndex = 4, showCount = 0))
        assertEquals(0, tonightSelectedIndex(firstVisibleItemIndex = -3, showCount = 5))
        assertEquals(2, tonightSelectedIndex(firstVisibleItemIndex = 2, showCount = 5))
        assertEquals(4, tonightSelectedIndex(firstVisibleItemIndex = 99, showCount = 5))
    }

    @Test
    fun carousel_keeps_shared_chrome_and_delegates_each_page_to_the_shared_card() {
        val source = String(Files.readAllBytes(homeScreenPath()))
        val carousel = functionSource(source, "FeaturedShowsCarousel")
        val movingPage = functionSource(source, "FeaturedShowHeroPage")
        val lazyRowIndex = carousel.indexOf("LazyRow(")

        assertTrue(lazyRowIndex >= 0)
        assertTrue(carousel.indexOf("Surface(") in 0 until lazyRowIndex)
        assertTrue(carousel.indexOf("text = headline.uppercase(Locale.US)") in 0 until lazyRowIndex)
        assertTrue(carousel.indexOf("TonightPageIndicator(") > lazyRowIndex)
        assertTrue(carousel.contains("rememberSnapFlingBehavior(lazyListState = listState)"))
        assertTrue(carousel.contains("onClick = { onOpenEntity(AppRoute.ShowDetail(item.show.id)) }"))

        assertTrue(movingPage.contains("TonightHeroCard("))
        assertTrue(movingPage.contains("TonightHeroCardContent("))
        assertTrue(movingPage.contains("onClick = onClick"))
        assertTrue(movingPage.contains("modifier.then("))
        assertTrue(source.contains("if (isTodayStyleDynamicShowRail(railKey))"))
        assertTrue(source.contains("FeaturedShowsCarousel("))
        assertTrue(source.contains("preferredHeadlinerId = preferredDynamicRailHeadlinerId(railKey, item)"))
        assertTrue(source.contains("timestampLabel = formatShowDateTime(item.show)"))
        assertTrue(source.contains("private fun FollowedComedianShowsRail("))
        assertTrue(source.contains("preferredHeadlinerId = preferredFavoriteHeadlinerId(show)"))
        assertTrue(movingPage.contains("item.timestampLabel ?: formatShowTime(show).orEmpty()"))
    }

    private fun homeScreenPath(): Path {
        val relativePaths =
            listOf(
                Paths.get(
                    "android/feature/home/src/main/kotlin/app/laughtrack/android/feature/home/HomeScreen.kt",
                ),
                Paths.get(
                    "feature/home/src/main/kotlin/app/laughtrack/android/feature/home/HomeScreen.kt",
                ),
            )

        return generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .flatMap { directory -> relativePaths.asSequence().map(directory::resolve) }
            .firstOrNull(Files::isRegularFile)
            ?: error("Unable to locate HomeScreen.kt from ${Paths.get("").toAbsolutePath()}")
    }

    private fun functionSource(
        source: String,
        functionName: String,
    ): String {
        val signatureStart = source.indexOf("fun $functionName(")
        require(signatureStart >= 0) { "Unable to find $functionName" }
        val bodyStart = source.indexOf('{', signatureStart)
        require(bodyStart >= 0) { "Unable to find $functionName body" }

        var depth = 0
        source.substring(bodyStart).forEachIndexed { offset, character ->
            when (character) {
                '{' -> depth += 1
                '}' -> {
                    depth -= 1
                    if (depth == 0) {
                        return source.substring(signatureStart, bodyStart + offset + 1)
                    }
                }
            }
        }

        error("Unable to find the end of $functionName")
    }
}
