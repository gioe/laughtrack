package app.laughtrack.android.core.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Smoke test that gives the CI unit-test job a real target and locks the shared
 * UiState contract that every feature ViewModel depends on.
 */
class UiStateTest {
    @Test
    fun success_holds_its_value() {
        val state: UiState<Int> = UiState.Success(42)
        assertTrue(state is UiState.Success)
        assertEquals(42, (state as UiState.Success).value)
    }

    @Test
    fun failure_holds_its_error() {
        val boom = IllegalStateException("boom")
        val state: UiState<Int> = UiState.Failure(boom)
        assertEquals(boom, (state as UiState.Failure).error)
    }

    @Test
    fun idle_and_loading_are_singletons() {
        assertEquals(UiState.Idle, UiState.Idle)
        assertEquals(UiState.Loading, UiState.Loading)
    }
}
