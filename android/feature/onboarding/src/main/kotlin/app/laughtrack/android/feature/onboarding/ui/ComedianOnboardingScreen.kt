package app.laughtrack.android.feature.onboarding.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.ui.components.RemoteImage
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComedianOnboardingScreen(
    onComplete: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ComedianOnboardingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val notificationPermissionLauncher =
        rememberLauncherForActivityResult(
            ActivityResultContracts.RequestPermission(),
        ) { granted ->
            viewModel.onPushPermissionResult(granted)
        }

    LaunchedEffect(state.isComplete) {
        if (state.isComplete) onComplete()
    }

    if (state.showSoftPushPrompt) {
        AlertDialog(
            onDismissRequest = viewModel::deferSoftPushPrompt,
            title = { Text("Get show alerts?") },
            text = { Text("LaughTrack can let you know when comedians you follow add shows near you.") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.softPushEnableTapped()
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else {
                            viewModel.dismissSoftPushPrompt()
                        }
                    },
                ) {
                    Text("Enable")
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::deferSoftPushPrompt) {
                    Text("Maybe later")
                }
            },
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        bottomBar = {
            ContinueBar(
                favoriteCount = state.favoriteCount,
                isSaving = state.isSaving,
                onContinue = viewModel::continueOnboarding,
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                "Pick comedians to follow",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Swipe through suggestions or search by name. " +
                    "Three favorites gives LaughTrack enough signal for better alerts.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            FavoriteProgress(state.favoriteCount)
            SearchBox(
                query = state.searchQuery,
                isSearchMode = state.isSearchMode,
                onQuery = viewModel::search,
            )
            NotificationToggles(
                emailEnabled = state.emailAlertsEnabled,
                pushEnabled = state.pushAlertsEnabled,
                onEmail = viewModel::setEmailAlertsEnabled,
                onPush = viewModel::setPushAlertsEnabled,
            )
            state.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error)
            }

            Box(Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) {
                when {
                    state.isLoading && state.visibleComedians.isEmpty() -> CircularProgressIndicator()
                    state.isSearchMode ->
                        SearchResults(
                            comedians = state.searchResults,
                            favorites = state.favorites,
                            onFavorite = viewModel::toggleFavorite,
                        )
                    else ->
                        SwipeDeck(
                            comedians = state.suggestions,
                            favorites = state.favorites,
                            passed = state.passed,
                            canRewind = state.passHistory.isNotEmpty(),
                            onFavorite = viewModel::toggleFavorite,
                            onPass = viewModel::passComedian,
                            onRewind = viewModel::rewindLastPass,
                            onMore = viewModel::loadMoreSuggestions,
                        )
                }
            }
        }
    }
}

@Composable
private fun FavoriteProgress(favoriteCount: Int) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        repeat(3) { index ->
            Box(
                Modifier
                    .size(12.dp)
                    .clip(RoundedCornerShape(50))
                    .background(
                        if (index < favoriteCount) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.surfaceVariant
                        },
                    ),
            )
        }
        Text(
            "$favoriteCount/3 selected",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
        )
    }
}

@Composable
private fun SearchBox(
    query: String,
    isSearchMode: Boolean,
    onQuery: (String) -> Unit,
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQuery,
        label = { Text("Search comedians") },
        singleLine = true,
        leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
        trailingIcon = {
            if (isSearchMode) {
                TextButton(onClick = { onQuery("") }) { Text("Deck") }
            }
        },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun NotificationToggles(
    emailEnabled: Boolean,
    pushEnabled: Boolean,
    onEmail: (Boolean) -> Unit,
    onPush: (Boolean) -> Unit,
) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        FilterChip(
            selected = emailEnabled,
            onClick = { onEmail(!emailEnabled) },
            label = { Text("Email alerts") },
        )
        FilterChip(
            selected = pushEnabled,
            onClick = { onPush(!pushEnabled) },
            label = { Text("Push alerts") },
        )
    }
}

@Composable
private fun SwipeDeck(
    comedians: List<ComedianSearchItem>,
    favorites: Map<String, Boolean>,
    passed: Set<String>,
    canRewind: Boolean,
    onFavorite: (String) -> Unit,
    onPass: (String) -> Unit,
    onRewind: () -> Unit,
    onMore: () -> Unit,
) {
    val top = comedians.firstOrNull { favorites[it.uuid] != true && it.uuid !in passed }
    if (top == null) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("No more cards in this deal.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (canRewind) {
                OutlinedButton(onClick = onRewind) { Text("Rewind") }
            }
            OutlinedButton(onClick = onMore) { Text("Deal more") }
        }
        return
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        ComedianCard(
            comedian = top,
            isFavorite = favorites[top.uuid] == true,
            onFavorite = { onFavorite(top.uuid) },
            onPass = { onPass(top.uuid) },
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(onClick = onRewind, enabled = canRewind) { Text("Rewind") }
            OutlinedButton(onClick = { onPass(top.uuid) }) { Text("Pass") }
            Button(onClick = { onFavorite(top.uuid) }) {
                Icon(Icons.Filled.Favorite, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Follow")
            }
        }
    }
}

@Composable
private fun SearchResults(
    comedians: List<ComedianSearchItem>,
    favorites: Map<String, Boolean>,
    onFavorite: (String) -> Unit,
) {
    if (comedians.isEmpty()) {
        Text("No matches yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        return
    }
    LazyColumn(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(comedians, key = { it.uuid }) { comedian ->
            ComedianRow(
                comedian = comedian,
                isFavorite = favorites[comedian.uuid] == true,
                onFavorite = { onFavorite(comedian.uuid) },
            )
        }
    }
}

@Composable
private fun ComedianCard(
    comedian: ComedianSearchItem,
    isFavorite: Boolean,
    onFavorite: () -> Unit,
    onPass: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var dragOffset by remember(comedian.uuid) { mutableFloatStateOf(0f) }
    Card(
        modifier =
            modifier
                .offset { IntOffset(dragOffset.roundToInt(), 0) }
                .pointerInput(comedian.uuid) {
                    detectHorizontalDragGestures(
                        onDragEnd = {
                            when {
                                dragOffset > SWIPE_THRESHOLD_PX -> onFavorite()
                                dragOffset < -SWIPE_THRESHOLD_PX -> onPass()
                            }
                            dragOffset = 0f
                        },
                        onHorizontalDrag = { _, dragAmount ->
                            dragOffset += dragAmount
                        },
                    )
                },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHighest),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            RemoteImage(
                url = comedian.imageUrl,
                contentDescription = comedian.name,
                modifier = Modifier.fillMaxWidth().height(260.dp).clip(RoundedCornerShape(12.dp)),
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(comedian.name, style = MaterialTheme.typography.titleLarge, maxLines = 1)
                    Text(
                        "${comedian.showCount} upcoming shows",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                FavoriteButton(isFavorite = isFavorite, onClick = onFavorite)
            }
        }
    }
}

private const val SWIPE_THRESHOLD_PX = 120f

@Composable
private fun ComedianRow(
    comedian: ComedianSearchItem,
    isFavorite: Boolean,
    onFavorite: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onFavorite).padding(8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        RemoteImage(
            url = comedian.imageUrl,
            contentDescription = comedian.name,
            modifier = Modifier.size(56.dp).clip(RoundedCornerShape(10.dp)),
        )
        Column(Modifier.weight(1f)) {
            Text(comedian.name, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${comedian.showCount} shows", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        FavoriteButton(isFavorite = isFavorite, onClick = onFavorite)
    }
}

@Composable
private fun FavoriteButton(
    isFavorite: Boolean,
    onClick: () -> Unit,
) {
    IconButton(onClick = onClick) {
        Icon(
            Icons.Filled.Favorite,
            contentDescription = if (isFavorite) "Remove favorite" else "Add favorite",
            tint = if (isFavorite) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ContinueBar(
    favoriteCount: Int,
    isSaving: Boolean,
    onContinue: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("$favoriteCount followed", modifier = Modifier.weight(1f))
        Button(onClick = onContinue, enabled = !isSaving) {
            Text(if (isSaving) "Saving..." else "Continue")
        }
    }
}
