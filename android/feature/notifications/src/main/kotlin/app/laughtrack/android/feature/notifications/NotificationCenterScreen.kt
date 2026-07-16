package app.laughtrack.android.feature.notifications

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.NotificationItem
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import app.laughtrack.android.core.ui.UiState
import java.time.ZonedDateTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationCenterScreen(
    onOpenEntity: (AppRoute) -> Unit,
    onBack: () -> Unit,
    viewModel: NotificationCenterViewModel = hiltViewModel(),
) {
    LaunchedEffect(Unit) { viewModel.load() }
    val state by viewModel.state.collectAsStateWithLifecycle()

    NotificationCenterContent(
        state = state,
        onOpenEntity = onOpenEntity,
        onBack = onBack,
        onRetry = viewModel::retry,
        onCardTapped = viewModel::onCardTapped,
    )
}

/** Render the real notification center from deterministic data without creating a Hilt ViewModel. */
@Composable
fun NotificationCenterScreen(
    onOpenEntity: (AppRoute) -> Unit,
    onBack: () -> Unit,
    dataOverride: NotificationListResponseData,
    referenceTime: ZonedDateTime,
) {
    NotificationCenterContent(
        state = UiState.Success(dataOverride),
        onOpenEntity = onOpenEntity,
        onBack = onBack,
        onRetry = {},
        onCardTapped = {},
        referenceTime = referenceTime,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NotificationCenterContent(
    state: UiState<NotificationListResponseData>,
    onOpenEntity: (AppRoute) -> Unit,
    onBack: () -> Unit,
    onRetry: () -> Unit,
    onCardTapped: (Int) -> Unit,
    referenceTime: ZonedDateTime? = null,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Notifications") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        val modifier = Modifier.padding(padding)
        when (val current = state) {
            is UiState.Failure -> CenteredMessage("Couldn't load notifications.", onRetry, modifier)
            is UiState.Success ->
                if (current.value.items.isEmpty()) {
                    CenteredMessage("No notifications yet.", null, modifier)
                } else {
                    NotificationList(
                        items = current.value.items,
                        onCardTap = { route, analyticsShowId ->
                            onCardTapped(analyticsShowId)
                            onOpenEntity(route)
                        },
                        modifier = modifier,
                        referenceTime = referenceTime,
                    )
                }
            else -> CenteredMessage("Loading…", null, modifier)
        }
    }
}

@Composable
private fun NotificationList(
    items: List<NotificationItem>,
    onCardTap: (AppRoute, Int) -> Unit,
    modifier: Modifier,
    referenceTime: ZonedDateTime? = null,
) {
    val now = remember(referenceTime) { referenceTime ?: ZonedDateTime.now() }
    LazyColumn(modifier.fillMaxSize()) {
        items(items, key = { it.id }) { item ->
            NotificationRow(item, now) { onCardTap(item.tapRoute(), item.analyticsShowId()) }
            HorizontalDivider()
        }
    }
}

/** A single-show entry opens that show; a grouped entry opens the Favorites tab
 *  (which lists the shows). Mirrors the grouped push's route key. */
private fun NotificationItem.tapRoute(): AppRoute =
    if (route == "favorites") {
        AppRoute.Favorites(shows.map { it.showId })
    } else {
        shows.firstOrNull()?.let { AppRoute.ShowDetail(it.showId) } ?: AppRoute.Favorites()
    }

/** Show id for the tap analytics event; 0 for a grouped (Favorites) tap. */
private fun NotificationItem.analyticsShowId(): Int = if (route == "favorites") 0 else shows.firstOrNull()?.showId ?: 0

@Composable
private fun NotificationRow(
    item: NotificationItem,
    now: ZonedDateTime,
    onClick: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        UnreadDot(item.isUnread)
        Column(Modifier.weight(1f)) {
            Text(item.title, style = MaterialTheme.typography.titleSmall)
            Text(
                item.body,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        formatTimeAgo(item.sentAt, now)?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun UnreadDot(isUnread: Boolean) {
    val color = if (isUnread) MaterialTheme.colorScheme.primary else Color.Transparent
    Box(
        Modifier
            .padding(top = 6.dp)
            .size(8.dp)
            .clip(CircleShape)
            .background(color),
    )
}

@Composable
private fun CenteredMessage(
    message: String,
    onRetry: (() -> Unit)?,
    modifier: Modifier,
) {
    Column(
        modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (onRetry != null) {
            TextButton(onClick = onRetry) { Text("Retry") }
        }
    }
}
