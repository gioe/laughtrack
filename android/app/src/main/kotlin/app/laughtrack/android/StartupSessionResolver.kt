package app.laughtrack.android

import app.laughtrack.android.core.network.generated.model.MeResponse
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

internal sealed interface StartupSessionState {
    data object Loading : StartupSessionState

    data object SignedOut : StartupSessionState

    data class Authenticated(val response: MeResponse) : StartupSessionState

    data object Failure : StartupSessionState
}

/** Resolves the destination-bearing account response before exposing authenticated UI. */
internal class StartupSessionResolver(
    private val scope: CoroutineScope,
    private val restoreSession: suspend () -> Boolean,
    private val getMe: suspend () -> Result<MeResponse>,
) {
    private val mutableState = MutableStateFlow<StartupSessionState>(StartupSessionState.Loading)
    val state: StateFlow<StartupSessionState> = mutableState.asStateFlow()

    private var job: Job? = null
    private var generation = 0L

    fun resolve() {
        val requestGeneration = ++generation
        job?.cancel()
        mutableState.value = StartupSessionState.Loading
        job =
            scope.launch {
                val resolved =
                    withTimeoutOrNull(RESOLUTION_TIMEOUT_MILLIS) { resolveSession() }
                        ?: StartupSessionState.Failure
                currentCoroutineContext().ensureActive()
                if (generation == requestGeneration) mutableState.value = resolved
            }
    }

    fun signedOut() {
        generation++
        job?.cancel()
        mutableState.value = StartupSessionState.SignedOut
    }

    fun completeOnboarding() {
        val current = mutableState.value as? StartupSessionState.Authenticated ?: return
        mutableState.value =
            current.copy(
                response = current.response.copy(data = current.response.data.copy(comedianOnboardingCompleted = true)),
            )
    }

    private suspend fun resolveSession(): StartupSessionState {
        return try {
            if (!restoreSession()) return StartupSessionState.SignedOut
            val response = getMe()
            // AuthSessionManager currently returns cancellation inside Result.
            currentCoroutineContext().ensureActive()
            val error = response.exceptionOrNull()
            if (error is CancellationException) throw error
            response.getOrNull()?.let(StartupSessionState::Authenticated) ?: failureState()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            failureState()
        }
    }

    private suspend fun failureState(): StartupSessionState =
        try {
            // The HTTP authenticator can clear rejected refresh tokens during /me.
            if (restoreSession()) StartupSessionState.Failure else StartupSessionState.SignedOut
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            StartupSessionState.Failure
        }

    private companion object {
        const val RESOLUTION_TIMEOUT_MILLIS = 15_000L
    }
}
