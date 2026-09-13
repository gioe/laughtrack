package app.laughtrack.android

import app.laughtrack.android.core.network.generated.model.MeData
import app.laughtrack.android.core.network.generated.model.MeResponse
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class StartupSessionResolverTest {
    @Test
    fun delayedCurrentUserKeepsStartupUnresolved() =
        runTest {
            val response = CompletableDeferred<Result<MeResponse>>()
            val resolver = StartupSessionResolver(backgroundScope, { true }, { response.await() })
            resolver.resolve()
            runCurrent()
            assertEquals(StartupSessionState.Loading, resolver.state.value)
            response.complete(Result.success(profile(completed = false)))
            runCurrent()
            assertEquals(StartupSessionState.Authenticated(profile(completed = false)), resolver.state.value)
        }

    @Test
    fun guestDoesNotFetchCurrentUser() =
        runTest {
            val resolver = StartupSessionResolver(backgroundScope, { false }, { error("Unexpected /me") })
            resolver.resolve()
            runCurrent()
            assertEquals(StartupSessionState.SignedOut, resolver.state.value)
        }

    @Test
    fun completedAccountResolvesWithOnboardingDecision() =
        runTest {
            val resolver = StartupSessionResolver(backgroundScope, { true }, { Result.success(profile(true)) })
            resolver.resolve()
            runCurrent()
            assertEquals(StartupSessionState.Authenticated(profile(true)), resolver.state.value)
        }

    @Test
    fun rejectedRefreshTokensResolveSignedOut() =
        runTest {
            var hasTokens = true
            val resolver =
                StartupSessionResolver(backgroundScope, { hasTokens }, {
                    hasTokens = false
                    Result.failure(IOException("Unauthorized"))
                })
            resolver.resolve()
            runCurrent()
            assertEquals(StartupSessionState.SignedOut, resolver.state.value)
        }

    @Test
    fun offlineAccountCanRetryWithoutDiscardingSession() =
        runTest {
            var online = false
            val resolver =
                StartupSessionResolver(backgroundScope, { true }, {
                    if (online) Result.success(profile(true)) else Result.failure(IOException("Offline"))
                })
            resolver.resolve()
            runCurrent()
            assertEquals(StartupSessionState.Failure, resolver.state.value)
            online = true
            resolver.resolve()
            assertEquals(StartupSessionState.Loading, resolver.state.value)
            runCurrent()
            assertEquals(StartupSessionState.Authenticated(profile(true)), resolver.state.value)
        }

    @Test
    fun stalledCurrentUserTimesOutIntoRecovery() =
        runTest {
            val never = CompletableDeferred<Result<MeResponse>>()
            val resolver = StartupSessionResolver(backgroundScope, { true }, { never.await() })
            resolver.resolve()
            runCurrent()
            advanceTimeBy(15_000)
            runCurrent()
            assertEquals(StartupSessionState.Failure, resolver.state.value)
        }

    @Test
    fun stalledTokenRestoreAlsoTimesOutIntoRecovery() =
        runTest {
            val never = CompletableDeferred<Boolean>()
            val resolver = StartupSessionResolver(backgroundScope, { never.await() }, { error("Unexpected /me") })
            resolver.resolve()
            runCurrent()
            advanceTimeBy(15_000)
            runCurrent()
            assertEquals(StartupSessionState.Failure, resolver.state.value)
        }

    @Test
    fun signOutRejectsLateResponseEvenWhenDependencySwallowsCancellation() =
        runTest {
            val delayed = CompletableDeferred<Result<MeResponse>>()
            val resolver =
                StartupSessionResolver(backgroundScope, { true }, {
                    withContext(NonCancellable) { delayed.await() }
                })
            resolver.resolve()
            runCurrent()
            resolver.signedOut()
            delayed.complete(Result.success(profile(false)))
            runCurrent()
            assertEquals(StartupSessionState.SignedOut, resolver.state.value)
        }

    @Test
    fun newerResolutionWinsOverLateResponse() =
        runTest {
            val delayed = CompletableDeferred<Result<MeResponse>>()
            var requests = 0
            val resolver =
                StartupSessionResolver(backgroundScope, { true }, {
                    if (requests++ == 0) {
                        withContext(
                            NonCancellable,
                        ) { delayed.await() }
                    } else {
                        Result.success(profile(true))
                    }
                })
            resolver.resolve()
            runCurrent()
            resolver.resolve()
            runCurrent()
            delayed.complete(Result.success(profile(false)))
            runCurrent()
            assertEquals(StartupSessionState.Authenticated(profile(true)), resolver.state.value)
        }

    @Test
    fun savedOnboardingCompletionUpdatesResolvedAccount() =
        runTest {
            val resolver = StartupSessionResolver(backgroundScope, { true }, { Result.success(profile(false)) })
            resolver.resolve()
            runCurrent()
            resolver.completeOnboarding()
            val authenticated = resolver.state.value as StartupSessionState.Authenticated
            assertTrue(authenticated.response.data.comedianOnboardingCompleted)
            assertEquals("user-1", authenticated.response.data.userId)
        }

    private fun profile(completed: Boolean) =
        MeResponse(
            MeData(
                userId = "user-1",
                email = "test@example.com",
                isAdmin = false,
                emailShowNotifications = false,
                pushShowNotifications = false,
                comedianOnboardingCompleted = completed,
                zipCode = null,
                nearbyDistanceMiles = null,
            ),
        )
}
