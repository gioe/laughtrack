package app.laughtrack.android.feature.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackTheme

/**
 * Placeholder Discover/Home surface. The real feed rails + location header land
 * in TASK-3259; this scaffold version proves module wiring and theme application
 * end-to-end so the app launches.
 */
@Composable
fun HomeScreen(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = "LaughTrack", style = MaterialTheme.typography.headlineLarge)
        Text(
            text = "Discover comedy near you",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Preview
@Composable
private fun HomeScreenPreview() {
    LaughTrackTheme {
        HomeScreen()
    }
}
