package app.laughtrack.android

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.components.UiStateContent

/**
 * Temporary tab body used until the real feature screens land (Search → TASK-3260,
 * Favorites → TASK-3261, Profile/Notifications → TASK-3266/3264). [onOpenSample],
 * when provided, navigates into the detail stack so the shell's push/dedup is
 * exercisable before real cards exist.
 */
@Composable
fun PlaceholderScreen(title: String, onOpenSample: (() -> Unit)? = null) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(title, style = MaterialTheme.typography.headlineMedium)
        Text(
            "Coming soon.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (onOpenSample != null) {
            TextButton(onClick = onOpenSample) { Text("Open a sample show") }
        }
    }
}

/**
 * Temporary entity-detail body reached via tab cards, deep links, and push routing.
 * Real detail screens land in TASK-3262; this renders through the shared
 * [UiStateContent] / [RemoteImage] / skeleton primitives so the shell proves they
 * are wired and reusable. It flips Loading → Success immediately (no fetch yet).
 */
@Composable
fun EntityDetailPlaceholder(entityType: String, id: Int, onBack: () -> Unit) {
    var state by remember(entityType, id) { mutableStateOf<UiState<String>>(UiState.Loading) }
    LaunchedEffect(entityType, id) { state = UiState.Success("$entityType #$id") }

    UiStateContent(state) { title ->
        Column(
            Modifier.fillMaxSize().padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            RemoteImage(
                url = null,
                contentDescription = null,
                modifier = Modifier.fillMaxWidth().height(220.dp),
            )
            Text(
                title,
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.padding(horizontal = 24.dp),
            )
            SkeletonLine(Modifier.padding(horizontal = 24.dp).fillMaxWidth(0.6f))
            TextButton(onClick = onBack, modifier = Modifier.padding(horizontal = 16.dp)) {
                Text("Back")
            }
        }
    }
}
