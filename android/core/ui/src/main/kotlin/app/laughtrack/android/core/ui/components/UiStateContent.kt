package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.UiState

/**
 * Renders a [UiState] through per-case slots so every feature screen handles
 * idle / loading / success / failure consistently — the Compose analog of the
 * iOS LoadPhase switch. [loading] and [failure] have sensible defaults so callers
 * usually supply only [success].
 */
@Composable
fun <T> UiStateContent(
    state: UiState<T>,
    modifier: Modifier = Modifier,
    loading: @Composable () -> Unit = { DefaultLoadingState(modifier) },
    failure: @Composable (Throwable) -> Unit = { DefaultErrorState(modifier) },
    idle: @Composable () -> Unit = {},
    success: @Composable (T) -> Unit,
) {
    when (state) {
        is UiState.Idle -> idle()
        is UiState.Loading -> loading()
        is UiState.Success -> success(state.value)
        is UiState.Failure -> failure(state.error)
    }
}

@Composable
private fun DefaultLoadingState(modifier: Modifier = Modifier) {
    Column(
        modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        repeat(4) { SkeletonLine() }
    }
}

@Composable
private fun DefaultErrorState(modifier: Modifier = Modifier) {
    Text(
        text = "Something went wrong. Pull to refresh.",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier.fillMaxSize().wrapContentSize(Alignment.Center).padding(24.dp),
    )
}
