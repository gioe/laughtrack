@file:Suppress("ktlint:standard:max-line-length")

package app.laughtrack.android.screenshots

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.os.SystemClock
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okio.Buffer
import java.util.Collections

/** Hermetic API and artwork backend for the Play Store screenshot journey. */
object ScreenshotFixtureServer {
    private const val API_PREFIX = "/api/v1/"
    private val requestedArtwork = Collections.synchronizedSet(mutableSetOf<String>())
    private val unexpectedRequests = Collections.synchronizedList(mutableListOf<String>())

    private val server =
        MockWebServer().apply {
            dispatcher = FixtureDispatcher
            start()
        }

    val apiBaseUrl: String
        get() = server.url(API_PREFIX).toString()

    fun artworkUrl(key: String): String = server.url("/artwork/$key.png").toString()

    fun awaitArtwork(
        key: String,
        timeoutMs: Long = 10_000,
    ) {
        val deadline = SystemClock.uptimeMillis() + timeoutMs
        while (key !in requestedArtwork && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(20)
        }
        check(key in requestedArtwork) { "Artwork '$key' was not requested within ${timeoutMs}ms" }
    }

    fun assertNoUnexpectedRequests() {
        check(unexpectedRequests.isEmpty()) {
            "Screenshot flow made unexpected requests: ${unexpectedRequests.joinToString()}"
        }
    }

    private object FixtureDispatcher : Dispatcher() {
        override fun dispatch(request: RecordedRequest): MockResponse {
            val path = request.requestUrl?.encodedPath.orEmpty()
            return when {
                path.startsWith("/artwork/") -> artworkResponse(path)
                path == "${API_PREFIX}home/feed" -> jsonResponse(homeFeedJson())
                path == "${API_PREFIX}shows/search" -> jsonResponse(showSearchJson())
                path == "${API_PREFIX}comedians/search" -> jsonResponse(comedianSearchJson())
                path == "${API_PREFIX}clubs/search" -> jsonResponse(clubSearchJson())
                path == "${API_PREFIX}podcasts/search" -> jsonResponse(podcastSearchJson())
                path == "${API_PREFIX}clubs/201" -> jsonResponse(clubDetailJson())
                path == "${API_PREFIX}clubs/201/shows" -> jsonResponse(clubShowsJson())
                path == "${API_PREFIX}shows/101" -> jsonResponse(showDetailJson())
                path == "${API_PREFIX}comedians/past-shows" -> jsonResponse(pastShowsJson())
                path == "${API_PREFIX}comedians/301/upcoming-runs" -> jsonResponse(upcomingRunsJson())
                path == "${API_PREFIX}comedians/301/co-bill" -> jsonResponse("{\"data\":[]}")
                path == "${API_PREFIX}comedians/301" -> jsonResponse(comedianDetailJson())
                path == "${API_PREFIX}podcasts/401" -> jsonResponse(podcastDetailJson())
                else -> {
                    unexpectedRequests += request.path.orEmpty()
                    MockResponse().setResponseCode(404).setBody("{\"error\":\"fixture not found\"}")
                }
            }
        }
    }

    private fun jsonResponse(body: String): MockResponse =
        MockResponse()
            .setHeader("Content-Type", "application/json")
            .setBody(body)

    private fun artworkResponse(path: String): MockResponse {
        val key = path.substringAfterLast('/').substringBeforeLast('.')
        requestedArtwork += key
        val (label, startColor, endColor) =
            when (key) {
                "taylor" -> Triple("TT", Color.rgb(118, 48, 91), Color.rgb(221, 103, 47))
                "comedy-store" -> Triple("CS", Color.rgb(42, 42, 42), Color.rgb(207, 75, 40))
                "ali-wong" -> Triple("AW", Color.rgb(181, 76, 119), Color.rgb(237, 181, 73))
                "joe-rogan" -> Triple("JRE", Color.rgb(167, 54, 29), Color.rgb(35, 35, 35))
                else -> Triple("LT", Color.DKGRAY, Color.rgb(221, 103, 47))
            }
        val bitmap = Bitmap.createBitmap(640, 640, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val background =
            Paint().apply {
                shader = android.graphics.LinearGradient(0f, 0f, 640f, 640f, startColor, endColor, android.graphics.Shader.TileMode.CLAMP)
            }
        canvas.drawRect(0f, 0f, 640f, 640f, background)
        val text =
            Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.WHITE
                textAlign = Paint.Align.CENTER
                textSize = if (label.length > 2) 190f else 250f
                typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            }
        canvas.drawText(label, 320f, 390f, text)
        val bytes = Buffer()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, bytes.outputStream())
        bitmap.recycle()
        return MockResponse().setHeader("Content-Type", "image/png").setBody(bytes)
    }

    private fun socialJson(
        id: Int,
        handle: String,
    ) = """{"id":$id,"instagramAccount":"$handle","website":"https://laughtrack.test/$handle"}"""

    private fun lineupJson(
        id: Int = 301,
        name: String = "Taylor Tomlinson",
        artKey: String = "taylor",
    ) = """{"id":$id,"uuid":"fixture-$id","name":"$name","imageUrl":"${artworkUrl(
        artKey,
    )}","showCount":40,"socialData":${socialJson(id, name.lowercase().replace(" ", ""))},"isFavorite":false}"""

    private fun showJson(
        id: Int = 101,
        name: String = "Taylor Tomlinson & Friends",
        hour: Int = 20,
    ) = """{"id":$id,"clubId":201,"date":"2026-07-10T${hour.toString().padStart(
        2,
        '0',
    )}:00:00.000Z","imageUrl":"${artworkUrl(
        "taylor",
    )}","clubName":"The Comedy Store","clubCity":"West Hollywood","clubState":"CA","name":"$name","room":"Main Room","timezone":"America/Los_Angeles","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://laughtrack.test/tickets/$id","soldOut":false,"type":"General Admission"}],"lineup":[${lineupJson()}]}"""

    private fun homeFeedJson(): String =
        """{"data":{"hero":{"zipCode":"90028","city":"Los Angeles","state":"CA","shows":[${showJson()}]},"trendingComedians":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"${artworkUrl(
            "ali-wong",
        )}","socialData":${socialJson(
            301,
            "aliwong",
        )},"showCount":28}],"comediansNearYou":[],"showsTonight":[${showJson()}],"moreNearYou":[${showJson(
            102,
            "Comedy Store Showcase",
            21,
        )}],"trendingThisWeek":[${showJson(
            103,
            "Best of Los Angeles",
            22,
        )}],"trendingPodcasts":[{"id":401,"slug":"joe-rogan-experience","title":"The Joe Rogan Experience","episodeCount":2520,"authorName":"Joe Rogan","imageUrl":"${artworkUrl(
            "joe-rogan",
        )}"}],"popularClubs":[{"id":201,"address":"8433 Sunset Blvd, West Hollywood, CA","name":"The Comedy Store","imageUrl":"${artworkUrl(
            "comedy-store",
        )}","activeComedianCount":120,"zipCode":"90069"}]}}"""

    private fun showSearchJson(): String {
        val shows =
            listOf(
                showJson(),
                showJson(102, "Comedy Store Showcase", 21),
                showJson(103, "Best of Los Angeles", 22),
                showJson(104, "Late Night at The Store", 23),
                showJson(105, "The Original Room", 19),
            ).joinToString()
        return """{"data":[$shows],"total":5,"filters":[],"zipCapTriggered":false}"""
    }

    private fun comedianSearchJson(): String {
        val comedians =
            listOf("Ali Wong", "Taylor Tomlinson", "Andrew Schulz", "Josh Johnson", "Trevor Noah")
                .mapIndexed { index, name ->
                    val id = 301 + index
                    val art = if (index == 0) "ali-wong" else "taylor"
                    """{"id":$id,"uuid":"fixture-$id","name":"$name","imageUrl":"${artworkUrl(
                        art,
                    )}","socialData":${socialJson(
                        id,
                        name.lowercase().replace(" ", ""),
                    )},"showCount":${28 - index},"isFavorite":false}"""
                }.joinToString()
        return """{"data":[$comedians],"total":5,"filters":[],"homeCityFilters":[]}"""
    }

    private fun clubSearchJson(): String {
        val clubs =
            listOf("The Comedy Store", "Comedy Cellar", "The Stand", "Hollywood Improv", "Largo at the Coronet")
                .mapIndexed { index, name ->
                    val id = 201 + index
                    """{"id":$id,"name":"$name","imageUrl":"${artworkUrl(
                        "comedy-store",
                    )}","address":"8433 Sunset Blvd","zipCode":"90069","showCount":${120 - index * 10},"activeComedianCount":${80 - index},"city":"West Hollywood","state":"CA","isFavorite":false}"""
                }.joinToString()
        return """{"data":[$clubs],"total":5,"filters":[]}"""
    }

    private fun podcastSearchJson(): String {
        val podcasts =
            listOf(
                "The Joe Rogan Experience",
                "Conan O'Brien Needs a Friend",
                "The JTrain Podcast",
                "WTF with Marc Maron",
                "SmartLess",
            )
                .mapIndexed { index, title ->
                    val id = 401 + index
                    """{"id":$id,"slug":"fixture-$id","title":"$title","episodeCount":${2520 - index * 100},"hosts":[{"id":301,"uuid":"fixture-301","name":"Joe Rogan","imageUrl":"${artworkUrl(
                        "joe-rogan",
                    )}"}],"authorName":"Comedy Podcast Network","imageUrl":"${artworkUrl(
                        "joe-rogan",
                    )}","description":"Stand-up conversations and new episodes every week.","isFavorite":false}"""
                }.joinToString()
        return """{"data":[$podcasts],"total":5,"filters":[]}"""
    }

    private fun clubDetailJson() =
        """{"data":{"id":201,"name":"The Comedy Store","imageUrl":"${artworkUrl(
            "comedy-store",
        )}","heroImageUrl":"${artworkUrl(
            "comedy-store",
        )}","website":"https://thecomedystore.com","address":"8433 Sunset Blvd, West Hollywood, CA","zipCode":"90069","phoneNumber":"(323) 650-6268"}}"""

    private fun clubShowsJson() =
        """{"data":[${showJson()},${showJson(
            102,
            "Comedy Store Showcase",
            21,
        )},${showJson(103, "Best of Los Angeles", 22)}],"total":3}"""

    private fun showDetailJson() =
        """{"data":{"id":101,"date":"2026-07-10T20:00:00.000Z","imageUrl":"${artworkUrl(
            "taylor",
        )}","showPageUrl":"https://laughtrack.test/show/101","club":{"id":201,"name":"The Comedy Store","imageUrl":"${artworkUrl(
            "comedy-store",
        )}","address":"8433 Sunset Blvd, West Hollywood, CA","timezone":"America/Los_Angeles"},"cta":{"label":"Buy tickets","isSoldOut":false,"url":"https://laughtrack.test/tickets/101"},"clubName":"The Comedy Store","tickets":[{"price":40,"purchaseUrl":"https://laughtrack.test/tickets/101","soldOut":false,"type":"General Admission"}],"name":"Taylor Tomlinson & Friends","lineup":[${lineupJson()}],"description":"A special night of new material and surprise guests.","room":"Main Room","soldOut":false,"timezone":"America/Los_Angeles"},"relatedShows":[]}"""

    private fun comedianDetailJson() =
        """{"data":{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"${artworkUrl(
            "ali-wong",
        )}","socialData":${socialJson(
            301,
            "aliwong",
        )},"podcastAppearances":[],"homeLocation":{"city":"San Francisco","state":"CA","country":"US"}}}"""

    private fun upcomingRunsJson() =
        """{"data":[{"clubId":201,"clubName":"The Comedy Store","clubImageUrl":"${artworkUrl(
            "comedy-store",
        )}","shows":[${showJson(106, "Ali Wong: Live", 20)}]}]}"""

    private fun pastShowsJson() = """{"data":[],"total":0}"""

    private fun podcastDetailJson() =
        """{"podcast":{"id":401,"slug":"joe-rogan-experience","title":"The Joe Rogan Experience","episodeCount":2520,"hosts":[{"id":401,"uuid":"fixture-host-401","name":"Joe Rogan","imageUrl":"${artworkUrl(
            "joe-rogan",
        )}"}],"authorName":"Joe Rogan","websiteUrl":"https://laughtrack.test/podcasts/jre","feedUrl":"https://laughtrack.test/feeds/jre","imageUrl":"${artworkUrl(
            "joe-rogan",
        )}","description":"Long-form conversations with comedians, artists, and fascinating guests.","isFavorite":false},"episodes":[{"id":501,"title":"#2520 - A Night of Comedy","description":"A conversation about stand-up and new material.","releaseDate":"2026-07-01","durationSeconds":8940,"episodeUrl":"https://laughtrack.test/episodes/501","audioUrl":"https://laughtrack.test/audio/501.mp3","appearances":[]},{"id":502,"title":"#2519 - Life on Tour","description":"Stories from the road.","releaseDate":"2026-06-27","durationSeconds":8700,"episodeUrl":"https://laughtrack.test/episodes/502","audioUrl":"https://laughtrack.test/audio/502.mp3","appearances":[]}],"relatedComedians":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"${artworkUrl(
            "ali-wong",
        )}","socialData":${socialJson(301, "aliwong")},"showCount":28,"isFavorite":false}]}"""
}
