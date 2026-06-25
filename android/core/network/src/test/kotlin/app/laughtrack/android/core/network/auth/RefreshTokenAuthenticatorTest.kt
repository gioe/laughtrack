package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

class RefreshTokenAuthenticatorTest {
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
    fun refreshesOnUnauthorizedAndRetriesOriginalRequest() =
        runTest {
            val store =
                InMemoryTokenStore(
                    SessionTokens(
                        accessToken = "old-access",
                        refreshToken = "old-refresh",
                        expiresAtEpochSeconds = 1,
                    ),
                )
            val clock = Clock.fixed(Instant.ofEpochSecond(2_000_000_000), ZoneOffset.UTC)
            val baseUrl = server.url("/api/v1/").toString()
            val refreshApi = apiWithClient(baseUrl, OkHttpClient())
            val authedClient =
                OkHttpClient.Builder()
                    .addInterceptor(AuthTokenInterceptor(store) { "America/New_York" })
                    .authenticator(
                        RefreshTokenAuthenticator(
                            tokenStore = store,
                            refreshApi = refreshApi,
                            clock = clock,
                        ),
                    )
                    .build()
            val authApi = apiWithClient(baseUrl, authedClient)

            server.enqueue(MockResponse().setResponseCode(401))
            server.enqueue(
                jsonResponse(
                    """{"accessToken":"new-access","refreshToken":"new-refresh","expiresIn":900}""",
                ),
            )
            server.enqueue(
                jsonResponse(
                    """
                    {
                      "data": {
                        "email": "android@example.com",
                        "isAdmin": false,
                        "emailShowNotifications": true,
                        "pushShowNotifications": false,
                        "comedianOnboardingCompleted": false,
                        "zipCode": "10001",
                        "nearbyDistanceMiles": 25,
                        "userId": "user_1"
                      }
                    }
                    """.trimIndent(),
                ),
            )

            val response = authApi.getMe()

            assertTrue(response.isSuccessful)
            assertEquals("android@example.com", response.body()?.data?.email)
            assertEquals(
                SessionTokens(
                    accessToken = "new-access",
                    refreshToken = "new-refresh",
                    expiresAtEpochSeconds = 2_000_000_900,
                ),
                store.read(),
            )

            val firstMe = server.takeRequest()
            assertEquals("/api/v1/me", firstMe.path)
            assertEquals("Bearer old-access", firstMe.getHeader("Authorization"))
            assertEquals("America/New_York", firstMe.getHeader("X-Timezone"))

            val refresh = server.takeRequest()
            assertEquals("/api/v1/auth/refresh", refresh.path)
            assertEquals(null, refresh.getHeader("Authorization"))
            assertEquals("""{"refreshToken":"old-refresh"}""", refresh.body.readUtf8())

            val retriedMe = server.takeRequest()
            assertEquals("/api/v1/me", retriedMe.path)
            assertEquals("Bearer new-access", retriedMe.getHeader("Authorization"))
        }

    @Test
    fun clearsTokensAndSurfaces401WhenRefreshFails() =
        runTest {
            val store =
                InMemoryTokenStore(
                    SessionTokens("old-access", "old-refresh", expiresAtEpochSeconds = 1),
                )
            val baseUrl = server.url("/api/v1/").toString()
            val authApi = authedApi(store, baseUrl)

            server.enqueue(MockResponse().setResponseCode(401)) // GET /me
            server.enqueue(MockResponse().setResponseCode(401)) // POST /auth/refresh fails

            val response = authApi.getMe()

            assertEquals(401, response.code())
            // A failed refresh must clear the session so the app falls back to sign-in.
            assertEquals(null, store.read())
        }

    @Test
    fun stopsAfterOneRetryWhenRefreshedTokenStillUnauthorized() =
        runTest {
            val store =
                InMemoryTokenStore(
                    SessionTokens("old-access", "old-refresh", expiresAtEpochSeconds = 1),
                )
            val baseUrl = server.url("/api/v1/").toString()
            val authApi = authedApi(store, baseUrl)

            server.enqueue(MockResponse().setResponseCode(401)) // GET /me
            server.enqueue(
                jsonResponse("""{"accessToken":"new-access","refreshToken":"new-refresh","expiresIn":900}"""),
            ) // refresh succeeds
            server.enqueue(MockResponse().setResponseCode(401)) // retried GET /me still 401

            val response = authApi.getMe()

            // MAX_AUTH_ATTEMPTS guard must stop the retry chain — no infinite refresh loop.
            assertEquals(401, response.code())
        }

    private fun authedApi(
        store: InMemoryTokenStore,
        baseUrl: String,
    ): AuthApi {
        val refreshApi = apiWithClient(baseUrl, OkHttpClient())
        val authedClient =
            OkHttpClient.Builder()
                .addInterceptor(AuthTokenInterceptor(store) { "UTC" })
                .authenticator(RefreshTokenAuthenticator(tokenStore = store, refreshApi = refreshApi))
                .build()
        return apiWithClient(baseUrl, authedClient)
    }

    private fun apiWithClient(
        baseUrl: String,
        okHttpClient: OkHttpClient,
    ): AuthApi =
        ApiClient(
            baseUrl = baseUrl,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        ).createService(AuthApi::class.java)

    private fun jsonResponse(body: String): MockResponse =
        MockResponse()
            .setResponseCode(200)
            .setHeader("Content-Type", "application/json")
            .setBody(body)
}
