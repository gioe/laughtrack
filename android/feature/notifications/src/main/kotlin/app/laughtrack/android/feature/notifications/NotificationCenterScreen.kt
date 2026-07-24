package app.laughtrack.android.feature.notifications

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.NotificationItem
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.theme.LaughTrackColors
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
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = { Text("Notifications") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
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
    var sortOrder by rememberSaveable { mutableStateOf(DEFAULT_NOTIFICATION_SORT_ORDER) }
    val sortedItems = remember(items, sortOrder) { sortOrder.sorted(items) }
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
        LazyColumn(
            modifier = Modifier.widthIn(max = NOTIFICATION_LIST_MAX_WIDTH).fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item(key = "notification-sort-control") {
                NotificationSortControl(
                    selected = sortOrder,
                    onSelect = { sortOrder = it },
                )
            }
            items(sortedItems, key = { it.id }) { item ->
                NotificationRow(item, now) { onCardTap(item.tapRoute(), item.analyticsShowId()) }
            }
        }
    }
}

@Composable
private fun NotificationSortControl(
    selected: NotificationSortOrder,
    onSelect: (NotificationSortOrder) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            "Sort notifications",
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.ForegroundMuted,
        )
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            NotificationSortOrder.entries.forEach { option ->
                FilterChip(
                    selected = option == selected,
                    onClick = { onSelect(option) },
                    label = { Text(option.label) },
                )
            }
        }
    }
}

internal enum class NotificationSortOrder(
    val label: String,
) {
    RECENT("Recent"),
    OLDEST("Oldest"),
    ;

    fun sorted(items: List<NotificationItem>): List<NotificationItem> =
        items.sortedWith(
            Comparator { lhs, rhs ->
                val lhsTimestamp = parseNotificationTimestamp(lhs.sentAt)
                val rhsTimestamp = parseNotificationTimestamp(rhs.sentAt)
                val timestampComparison =
                    when {
                        lhsTimestamp == null && rhsTimestamp == null -> 0
                        lhsTimestamp == null -> 1
                        rhsTimestamp == null -> -1
                        this == RECENT -> rhsTimestamp.compareTo(lhsTimestamp)
                        else -> lhsTimestamp.compareTo(rhsTimestamp)
                    }
                timestampComparison.takeIf { it != 0 } ?: lhs.id.compareTo(rhs.id)
            },
        )
}

internal val DEFAULT_NOTIFICATION_SORT_ORDER = NotificationSortOrder.RECENT

/** A single-show entry opens that show; a grouped entry opens the Favorites tab
 *  (which lists the shows). Mirrors the grouped push's route key. */
internal fun NotificationItem.tapRoute(): AppRoute =
    if (route == "favorites") {
        AppRoute.Favorites(shows.map { it.showId })
    } else {
        shows.firstOrNull()?.let { AppRoute.ShowDetail(it.showId) } ?: AppRoute.Favorites()
    }

/** Show id for the tap analytics event; 0 for a grouped (Favorites) tap. */
internal fun NotificationItem.analyticsShowId(): Int = if (route == "favorites") 0 else shows.firstOrNull()?.showId ?: 0

@Composable
private fun NotificationRow(
    item: NotificationItem,
    now: ZonedDateTime,
    onClick: () -> Unit,
) {
    val presentation = notificationRowPresentation(item, now)
    val containerColor =
        if (presentation.isUnread) {
            LaughTrackColors.SurfaceElevated
        } else {
            LaughTrackColors.SurfaceMuted.copy(alpha = 0.92f)
        }
    val borderColor =
        if (presentation.isUnread) {
            LaughTrackColors.AccentStrong.copy(alpha = 0.55f)
        } else {
            LaughTrackColors.BorderSubtle
        }

    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = containerColor,
        border = BorderStroke(1.dp, borderColor),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            NotificationSourceAvatar(item, presentation.isUnread)
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (presentation.isUnread) {
                        Text(
                            "NEW",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = LaughTrackColors.AccentStrong,
                        )
                    }
                    Text(
                        presentation.source,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.labelMedium,
                        color = LaughTrackColors.ForegroundMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    presentation.relativeTime?.let { relativeTime ->
                        Text(
                            relativeTime,
                            style = MaterialTheme.typography.labelSmall,
                            color = LaughTrackColors.ForegroundMuted,
                        )
                    }
                }
                Text(
                    presentation.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = if (presentation.isUnread) FontWeight.Bold else FontWeight.SemiBold,
                    color = LaughTrackColors.Foreground,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
                presentation.body?.let { body ->
                    Text(
                        body,
                        style = MaterialTheme.typography.bodyMedium,
                        color = LaughTrackColors.ForegroundMuted,
                        maxLines = 4,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = LaughTrackColors.ForegroundMuted,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun NotificationSourceAvatar(
    item: NotificationItem,
    isUnread: Boolean,
) {
    Box {
        RemoteImage(
            url = item.comedianImageUrl,
            contentDescription = null,
            fallback = RemoteImageFallback.Comedian,
            modifier =
                Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .border(1.dp, LaughTrackColors.BorderSubtle, CircleShape),
        )
        if (isUnread) {
            Box(
                Modifier
                    .align(Alignment.TopEnd)
                    .size(11.dp)
                    .clip(CircleShape)
                    .background(LaughTrackColors.AccentStrong)
                    .border(2.dp, LaughTrackColors.SurfaceElevated, CircleShape),
            )
        }
    }
}

internal data class NotificationRowPresentation(
    val title: String,
    val body: String?,
    val source: String,
    val relativeTime: String?,
    val isUnread: Boolean,
)

internal fun notificationRowPresentation(
    item: NotificationItem,
    now: ZonedDateTime,
): NotificationRowPresentation {
    val comedianNames =
        item.comedians
            .map { it.comedianName.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
    val source =
        when {
            comedianNames.size > 1 -> "${comedianNames.first()} + ${comedianNames.size - 1} more"
            comedianNames.size == 1 -> comedianNames.first()
            item.comedianName.isNotBlank() -> item.comedianName.trim()
            else -> "Favorite comedians"
        }
    return NotificationRowPresentation(
        title = item.title,
        body = item.body.takeIf { it.isNotBlank() },
        source = source,
        relativeTime = formatTimeAgo(item.sentAt, now),
        isUnread = item.isUnread,
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

private val NOTIFICATION_LIST_MAX_WIDTH = 720.dp
