package app.laughtrack.android.feature.detail.ui.components

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.components.TicketDashedDivider
import app.laughtrack.android.core.ui.components.TicketDateParts
import app.laughtrack.android.core.ui.components.TicketStub
import app.laughtrack.android.core.ui.components.TicketStubColors
import app.laughtrack.android.core.ui.theme.LaughTrackColors

/**
 * Detail-screen chrome: a top bar with a back affordance and an optional trailing
 * action (Share), over a scrollable [content] slot. Shared by all four screens.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScaffold(
    title: String,
    onBack: () -> Unit,
    onShare: (() -> Unit)? = null,
    content: @Composable (Modifier) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (onShare != null) {
                        TextButton(onClick = onShare) { Text("Share") }
                    }
                },
            )
        },
    ) { padding ->
        content(Modifier.padding(padding))
    }
}

/** Full-width hero image used at the top of each detail body. */
@Composable
fun DetailHero(
    url: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
) {
    RemoteImage(
        url = url,
        contentDescription = contentDescription,
        modifier = modifier.fillMaxWidth().height(220.dp),
    )
}

/** A bold section header, e.g. "Lineup", "Upcoming", "Episodes". */
@Composable
fun SectionHeader(
    text: String,
    modifier: Modifier = Modifier,
) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        modifier = modifier,
    )
}

/** A label/value info row (e.g. "Venue" / club name) for fact lists. */
@Composable
fun InfoRow(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxWidth()) {
        Text(
            label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}

/**
 * A circular avatar with a caption, tappable to open the entity it represents.
 * Used for lineup, co-bill, hosts, and related-comedian rails.
 */
@Composable
fun EntityAvatar(
    name: String,
    imageUrl: String?,
    subtitle: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier
            .width(96.dp)
            .clickable(onClick = onClick)
            .padding(vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        RemoteImage(
            url = imageUrl,
            contentDescription = name,
            modifier = Modifier.size(80.dp).clip(CircleShape),
        )
        Text(
            name,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        subtitle?.let {
            Text(
                it,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/**
 * A horizontal show/event row with thumbnail, title, and subtitle, tappable to
 * open the show. Used for related shows, upcoming runs, and past shows.
 */
@Composable
fun ShowRow(
    title: String,
    subtitle: String?,
    imageUrl: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RemoteImage(
            url = imageUrl,
            contentDescription = title,
            modifier = Modifier.size(56.dp).clip(RoundedCornerShape(8.dp)),
        )
        Column(Modifier.weight(1f)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            subtitle?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

/**
 * A compact cream "ticket" show row mirroring the iOS ShowRow `.compactTicket`
 * presentation: paper body with artwork + title/subtitle, a dashed perforation,
 * and a date stub, all drawn with the shared LaughTrackColors.Ticket* tokens.
 * Used for the Comedian-detail upcoming/past show lists and the Show-detail
 * "More shows" list. Non-show lists (e.g. podcast appearances) keep the plain
 * [ShowRow] — they are not ticketed events.
 */
@Composable
fun TicketShowRow(
    title: String,
    subtitle: String?,
    imageUrl: String?,
    dateParts: TicketDateParts,
    priceLabel: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier =
            modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Min)
                .clip(RoundedCornerShape(12.dp))
                .clickable(onClick = onClick)
                .border(1.dp, LaughTrackColors.TicketBorder, RoundedCornerShape(12.dp)),
        color = LaughTrackColors.TicketPaper,
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 88.dp),
        ) {
            Row(
                modifier =
                    Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .padding(10.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    url = imageUrl,
                    contentDescription = title,
                    modifier = Modifier.size(56.dp).clip(RoundedCornerShape(8.dp)),
                )
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        title,
                        style = MaterialTheme.typography.titleSmall,
                        color = LaughTrackColors.TicketInk,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    subtitle?.takeIf { it.isNotBlank() }?.let {
                        Text(
                            it,
                            style = MaterialTheme.typography.bodySmall,
                            color = LaughTrackColors.TicketInkMuted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
            TicketDashedDivider(
                color = LaughTrackColors.TicketBorder,
                modifier =
                    Modifier
                        .fillMaxHeight()
                        .padding(vertical = 10.dp),
            )
            TicketStub(
                dateParts = dateParts,
                priceLabel = priceLabel,
                colors =
                    TicketStubColors(
                        background = LaughTrackColors.TicketStub,
                        accent = LaughTrackColors.TicketAccent,
                        primary = LaughTrackColors.TicketInk,
                        muted = LaughTrackColors.TicketInkMuted,
                    ),
                modifier =
                    Modifier
                        .width(88.dp)
                        .fillMaxHeight(),
            )
        }
    }
}

/**
 * Semantics tag on the detail loading skeleton so instrumented tests — notably
 * AppStoreScreenshotTest — can wait for the skeleton to disappear (content loaded)
 * before capturing a detail-screen frame. Inert at runtime.
 */
const val DETAIL_LOADING_TEST_TAG = "detailLoading"

/** Centered loading skeleton for the detail body. */
@Composable
fun DetailLoading(modifier: Modifier = Modifier) {
    Column(
        modifier.fillMaxSize().padding(24.dp).testTag(DETAIL_LOADING_TEST_TAG),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SkeletonLine(Modifier.fillMaxWidth().height(180.dp))
        repeat(4) { SkeletonLine() }
    }
}

/** Centered error state with a retry affordance. */
@Composable
fun DetailError(
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            "Couldn't load this page.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        TextButton(onClick = onRetry) { Text("Retry") }
    }
}
