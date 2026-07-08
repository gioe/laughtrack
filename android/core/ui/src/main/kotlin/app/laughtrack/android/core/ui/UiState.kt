package app.laughtrack.android.core.ui

/**
 * Shared async-load state used by every ViewModel, mirroring the iOS LoadPhase
 * enum (idle -> loading -> success / failure). Feature view models expose a
 * StateFlow<UiState<T>> and the UI renders per case.
 *
 * Lives in :core:ui (the design-system module) because it is a pure UI-phase
 * type consumed by [app.laughtrack.android.core.ui.components.UiStateContent];
 * keeping it here is what lets :core:ui avoid depending on :core:data.
 */
sealed interface UiState<out T> {
    data object Idle : UiState<Nothing>

    data object Loading : UiState<Nothing>

    data class Success<T>(val value: T) : UiState<T>

    data class Failure(val error: Throwable) : UiState<Nothing>
}
