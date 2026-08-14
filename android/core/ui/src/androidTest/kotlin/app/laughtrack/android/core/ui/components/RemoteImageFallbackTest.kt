package app.laughtrack.android.core.ui.components

import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertContentDescriptionEquals
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.junit4.ComposeContentTestRule
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import coil.Coil
import coil.ImageLoader
import coil.decode.DataSource
import coil.intercept.Interceptor
import coil.request.ErrorResult
import coil.request.ImageResult
import coil.request.SuccessResult
import kotlinx.coroutines.awaitCancellation
import org.junit.After
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException

/**
 * Drives RemoteImage through its four terminal/transient states with
 * deterministic Coil interceptors (no network): null URL, failed load,
 * in-flight load, and successful load.
 */
@RunWith(AndroidJUnit4::class)
class RemoteImageFallbackTest {
    @get:Rule
    val compose = createComposeRule()

    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @After
    fun resetImageLoader() {
        Coil.setImageLoader(ImageLoader.Builder(context).build())
    }

    @Test
    fun nullUrl_rendersEntityFallback() {
        compose.setContent {
            RemoteImage(
                url = null,
                contentDescription = "artwork",
                modifier = Modifier.size(120.dp),
                fallback = RemoteImageFallback.Comedian,
            )
        }

        compose.waitForTag(RemoteImageTestTags.fallback(RemoteImageFallback.Comedian))
        compose.onNodeWithTag(RemoteImageTestTags.fallback(RemoteImageFallback.Comedian)).assertIsDisplayed()
    }

    @Test
    fun imageLessEntityArtwork_rendersDistinctProminentFallbacks() {
        compose.setContent {
            Column {
                EntityArtwork(
                    artworkUrl = null,
                    kind = SearchEntityKind.SHOW,
                    artworkSize = 56.dp,
                )
                SearchEntityKind.entries
                    .filterNot { it == SearchEntityKind.SHOW }
                    .forEach { kind ->
                        EntityArtwork(
                            artworkUrl = " ",
                            kind = kind,
                        )
                    }
            }
        }

        SearchEntityKind.entries.forEach { kind ->
            compose
                .onNodeWithTag(RemoteImageTestTags.fallback(kind.fallback))
                .assertIsDisplayed()
            compose
                .onNodeWithTag(EntityArtworkTestTags.icon(kind), useUnmergedTree = true)
                .assertIsDisplayed()
                .assertWidthIsEqualTo(if (kind == SearchEntityKind.SHOW) 28.dp else 33.dp)
                .assertHeightIsEqualTo(if (kind == SearchEntityKind.SHOW) 28.dp else 33.dp)
        }
    }

    @Test
    fun imageLessNamedShowsAndComedians_renderDistinctCuratedLocalArtwork() {
        val fixtures =
            listOf(
                Triple(SearchEntityKind.SHOW, "Atsuko Okatsuka: Full Grown Tour", "AO"),
                Triple(SearchEntityKind.SHOW, "Josh Johnson and Friends", "JJ"),
                Triple(SearchEntityKind.COMEDIAN, "Taylor Tomlinson", "TT"),
                Triple(SearchEntityKind.COMEDIAN, "Sam Jay", "SJ"),
            )
        compose.setContent {
            Column {
                fixtures.forEach { (kind, identity, _) ->
                    EntityArtwork(
                        artworkUrl = "",
                        kind = kind,
                        artworkIdentity = identity,
                        contentDescription = "$identity artwork",
                    )
                }
            }
        }

        fixtures.forEach { (kind, identity, initials) ->
            compose
                .onNodeWithTag(EntityArtworkTestTags.curated(kind, identity), useUnmergedTree = true)
                .assertIsDisplayed()
            compose
                .onNodeWithTag(EntityArtworkTestTags.monogram(kind, identity), useUnmergedTree = true)
                .assertIsDisplayed()
            compose.onAllNodesWithText(initials, useUnmergedTree = true).assertCountEquals(0)
            compose
                .onNodeWithContentDescription("$identity artwork")
                .assertContentDescriptionEquals("$identity artwork")
        }
        compose.onAllNodesWithTag(EntityArtworkTestTags.icon(SearchEntityKind.SHOW), useUnmergedTree = true)
            .assertCountEquals(0)
        compose.onAllNodesWithTag(EntityArtworkTestTags.icon(SearchEntityKind.COMEDIAN), useUnmergedTree = true)
            .assertCountEquals(0)
        compose.onAllNodesWithTag(RemoteImageTestTags.SKELETON).assertCountEquals(0)
    }

    @Test
    fun failedLoad_rendersEntityFallback() {
        installLoader { chain ->
            ErrorResult(drawable = null, request = chain.request, throwable = IOException("network down"))
        }
        compose.setContent {
            RemoteImage(
                url = "https://example.com/club.jpg",
                contentDescription = "artwork",
                modifier = Modifier.size(120.dp),
                fallback = RemoteImageFallback.Club,
            )
        }

        compose.waitForTag(RemoteImageTestTags.fallback(RemoteImageFallback.Club))
        compose.onNodeWithTag(RemoteImageTestTags.fallback(RemoteImageFallback.Club)).assertIsDisplayed()
        compose.onAllNodesWithTag(RemoteImageTestTags.SKELETON).assertCountEquals(0)
    }

    @Test
    fun loading_showsSkeletonDistinctFromFallback() {
        installLoader { awaitCancellation() }
        compose.setContent {
            RemoteImage(
                url = "https://example.com/show.jpg",
                contentDescription = "artwork",
                modifier = Modifier.size(120.dp),
                fallback = RemoteImageFallback.Show,
            )
        }

        compose.waitForTag(RemoteImageTestTags.SKELETON)
        compose.onNodeWithTag(RemoteImageTestTags.SKELETON).assertIsDisplayed()
        compose.onAllNodesWithTag(RemoteImageTestTags.fallback(RemoteImageFallback.Show)).assertCountEquals(0)
    }

    @Test
    fun successfulLoad_showsImageWithoutSkeletonOrFallback() {
        installLoader { chain ->
            SuccessResult(
                drawable = ColorDrawable(Color.RED),
                request = chain.request,
                dataSource = DataSource.MEMORY,
            )
        }
        compose.setContent {
            RemoteImage(
                url = "https://example.com/podcast.jpg",
                contentDescription = "artwork",
                modifier = Modifier.size(120.dp),
                fallback = RemoteImageFallback.Podcast,
            )
        }

        compose.waitUntil(TIMEOUT_MS) {
            compose.onAllNodesWithTag(RemoteImageTestTags.SKELETON).fetchSemanticsNodes().isEmpty()
        }
        compose.onAllNodesWithTag(RemoteImageTestTags.fallback(RemoteImageFallback.Podcast)).assertCountEquals(0)
    }

    private fun installLoader(interceptor: suspend (Interceptor.Chain) -> ImageResult) {
        val loader =
            ImageLoader.Builder(context)
                .components { add(Interceptor { chain -> interceptor(chain) }) }
                .build()
        Coil.setImageLoader(loader)
    }

    private fun ComposeContentTestRule.waitForTag(tag: String) {
        waitUntil(TIMEOUT_MS) { onAllNodesWithTag(tag).fetchSemanticsNodes().isNotEmpty() }
    }

    private companion object {
        const val TIMEOUT_MS = 5_000L
    }
}
