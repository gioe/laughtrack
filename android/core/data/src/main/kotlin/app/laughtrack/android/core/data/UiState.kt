package app.laughtrack.android.core.data

import kotlinx.coroutines.CancellationException

/**
 * Shared async-load state used by every ViewModel, mirroring the iOS LoadPhase
 * enum (idle -> loading -> success / failure). Feature view models expose a
 * StateFlow<UiState<T>> and the UI renders per case.
 */
sealed interface UiState<out T> {
    data object Idle : UiState<Nothing>

    data object Loading : UiState<Nothing>

    data class Success<T>(val value: T) : UiState<T>

    data class Failure(val error: Throwable) : UiState<Nothing>
}

/**
 * Like [runCatching], but preserves structured coroutine cancellation.
 */
suspend inline fun <T> runCatchingCancellable(crossinline block: suspend () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (error: CancellationException) {
        throw error
    } catch (error: Throwable) {
        Result.failure(error)
    }
