package app.laughtrack.android.core.network.home

import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class HomeFeedApiTest {
    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun default_platform_query_uses_lowercase_android_wire_value() =
        runTest {
            server.enqueue(
                MockResponse()
                    .setResponseCode(200)
                    .setHeader("Content-Type", "application/json")
                    .setBody(EMPTY_FEED_RESPONSE),
            )
            val api =
                ApiClient(baseUrl = server.url("/api/v1/").toString())
                    .createService(HomeFeedApi::class.java)

            api.getHomeFeed(zip = "10001", distance = 50)

            assertEquals(
                "/api/v1/home/feed?zip=10001&distance=50&platform=android",
                server.takeRequest().path,
            )
        }

    private companion object {
        val EMPTY_FEED_RESPONSE =
            """
            {
              "data": {
                "hero": { "shows": [] },
                "trendingComedians": [],
                "comediansNearYou": [],
                "showsTonight": [],
                "moreNearYou": [],
                "trendingThisWeek": [],
                "followedComedianShows": [],
                "trendingPodcasts": [],
                "popularClubs": []
              }
            }
            """.trimIndent()
    }
}
