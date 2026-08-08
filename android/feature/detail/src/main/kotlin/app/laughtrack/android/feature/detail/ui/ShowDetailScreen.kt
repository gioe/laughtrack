package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.ShowDetail
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import app.laughtrack.android.feature.detail.ui.components.AdaptiveDetailCatalogLayout
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.util.addEventToCalendar
import app.laughtrack.android.feature.detail.util.formatShowDateTime
import app.laughtrack.android.feature.detail.util.formatTicketPriceLabel
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.parseShowDateTime
import app.laughtrack.android.feature.detail.util.showRowTitleSubtitle
import kotlinx.coroutines.delay
import java.math.BigDecimal
import java.time.Instant

@Composable
fun ShowDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    onHome: (() -> Unit)? = null,
    viewModel: ShowDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val isAdmin by viewModel.isAdmin.collectAsStateWithLifecycle()
    val savedShows by viewModel.savedShowsSnapshot.collectAsStateWithLifecycle()
    val savedShowMessage by viewModel.savedShowMessage.collectAsStateWithLifecycle()

    Box(Modifier.fillMaxSize()) {
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success ->
                ShowDetailBody(
                    ui = (state as UiState.Success<ShowDetailUi>).value,
                    isAdmin = isAdmin,
                    isSaved = savedShows.values[id] ?: false,
                    isSavedPending = id in savedShows.pending,
                    savedShowMessage = savedShowMessage,
                    onBack = onBack,
                    onHome = onHome,
                    onOpenEntity = onOpenEntity,
                    onToggleSaved = { viewModel.toggleSaved(id) },
                    onClearSavedShowMessage = viewModel::clearSavedShowMessage,
                )
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun ShowDetailBody(
    ui: ShowDetailUi,
    isAdmin: Boolean,
    isSaved: Boolean,
    isSavedPending: Boolean,
    savedShowMessage: String?,
    onBack: () -> Unit,
    onHome: (() -> Unit)?,
    onOpenEntity: (AppRoute) -> Unit,
    onToggleSaved: () -> Unit,
    onClearSavedShowMessage: () -> Unit,
) {
    val show = ui.detail
    val context = LocalContext.current
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 28.dp),
    ) {
        AdaptiveDetailCatalogLayout(
            hero = {
                ShowMarqueeHero(
                    show = show,
                    onBack = onBack,
                    onHome = onHome,
                    isSaved = isSaved,
                    isSavedPending = isSavedPending,
                    onToggleSaved = onToggleSaved,
                )
            },
            content = {
                Column(
                    Modifier.padding(horizontal = 8.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    if (isAdmin) {
                        AdminShowIdBadge(showId = show.id)
                    }
                    savedShowMessage?.let { message ->
                        AssistChip(
                            onClick = onClearSavedShowMessage,
                            label = { Text(message) },
                        )
                    }
                    ShowTicketSummary(
                        show = show,
                        ticketOutboundUrl = ui.ticketOutboundUrl,
                        onVenue = { onOpenEntity(AppRoute.ClubDetail(show.club.id)) },
                        onCalendar = {
                            parseShowDateTime(show.date, show.venueTimezone())
                                ?.toInstant()
                                ?.toEpochMilli()
                                ?.let { start ->
                                    context.addEventToCalendar(
                                        title = show.name ?: show.club.name,
                                        startMillis = start,
                                        endMillis = null,
                                        location =
                                            listOfNotNull(show.club.name, show.club.address)
                                                .joinToString(", "),
                                        description = "Added from LaughTrack.",
                                    )
                                }
                        },
                        onTickets = { url -> context.openUrl(url) },
                    )

                    if (!showDetailIsOpenMic(show)) {
                        ShowLineupSection(show.lineup.orEmpty(), onOpenEntity)
                    }
                    RelatedShowsSection(ui.relatedShows, onOpenEntity)
                }
            },
        )
    }
}

/** Admin-only copyable Show-ID chip on Show Detail (gated on isAdmin, mirrors iOS AdminShowIDBadge). */
@Composable
private fun AdminShowIdBadge(showId: Int) {
    val clipboard = LocalClipboardManager.current
    var copied by remember(showId) { mutableStateOf(false) }
    // Revert the "copied" confirmation after a moment so the chip doesn't stick.
    LaunchedEffect(copied) {
        if (copied) {
            delay(1_500)
            copied = false
        }
    }
    Surface(
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(999.dp),
        modifier =
            Modifier
                .clip(RoundedCornerShape(999.dp))
                .clickable {
                    clipboard.setText(AnnotatedString(showId.toString()))
                    copied = true
                }
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp)),
    ) {
        Text(
            text = if (copied) "Show ID $showId · copied" else "Show ID $showId · tap to copy",
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.ForegroundMuted,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        )
    }
}

@Composable
private fun ShowMarqueeHero(
    show: ShowDetail,
    onBack: () -> Unit,
    onHome: (() -> Unit)?,
    isSaved: Boolean,
    isSavedPending: Boolean,
    onToggleSaved: () -> Unit,
) {
    val heroComedian = showDetailHeroComedian(show)
    val heroImage = showDetailHeroImageUrl(show)
    Column(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    colors =
                        listOf(
                            Color(0xFF70451F),
                            Color(0xFF321B13),
                            LaughTrackColors.Canvas,
                        ),
                ),
            ),
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                FloatingChromeButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
                onHome?.let {
                    FloatingChromeButton(onClick = it) {
                        Icon(Icons.Filled.Home, contentDescription = "Home")
                    }
                }
            }
            if (showDetailSavedActionVisible(show, isSaved)) {
                FloatingChromeButton(
                    onClick = onToggleSaved,
                    enabled = !isSavedPending,
                ) {
                    if (isSavedPending) {
                        CircularProgressIndicator(
                            modifier =
                                Modifier
                                    .size(18.dp)
                                    .semantics { contentDescription = "Updating saved show" },
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Icon(
                            imageVector = if (isSaved) Icons.Filled.Bookmark else Icons.Filled.BookmarkBorder,
                            contentDescription = if (isSaved) "Remove saved show" else "Save show",
                            tint = if (isSaved) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                        )
                    }
                }
            }
        }

        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(start = 16.dp, end = 16.dp, bottom = 18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                showDetailDisplayTitle(show).uppercase(),
                style =
                    MaterialTheme.typography.headlineSmall.copy(
                        fontWeight = FontWeight.Black,
                        fontSize = 18.sp,
                        lineHeight = 22.sp,
                    ),
                color = LaughTrackColors.Foreground,
                textAlign = TextAlign.Center,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            if (heroComedian != null) {
                FramedComedianPoster(
                    url = heroImage,
                    caption = heroComedian.name,
                    contentDescription = showDetailDisplayTitle(show),
                )
            } else {
                DottedPoster(url = heroImage, contentDescription = showDetailDisplayTitle(show))
            }
        }
    }
}

@Composable
private fun FramedComedianPoster(
    url: String?,
    caption: String,
    contentDescription: String?,
) {
    Column(
        modifier =
            Modifier
                .width(220.dp)
                .background(Color(0xFFE1D8C7), RoundedCornerShape(8.dp))
                .border(2.dp, Color(0xFF5A554D), RoundedCornerShape(8.dp))
                .padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        RemoteImage(
            url = url,
            fallback = RemoteImageFallback.Comedian,
            contentDescription = contentDescription,
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(190.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.55f), RoundedCornerShape(2.dp)),
        )
        Text(
            caption.uppercase(),
            modifier = Modifier.fillMaxWidth().background(Color(0xFFF0E9DC)).padding(vertical = 4.dp),
            style =
                MaterialTheme.typography.labelLarge.copy(
                    fontFamily = FontFamily.Serif,
                    fontWeight = FontWeight.Bold,
                ),
            color = Color(0xFF4C463E),
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun DottedPoster(
    url: String?,
    contentDescription: String?,
) {
    Box(
        modifier =
            Modifier
                .size(210.dp)
                .border(3.dp, LaughTrackColors.AccentStrong, RoundedCornerShape(18.dp))
                .padding(10.dp),
    ) {
        RemoteImage(
            url = url,
            fallback = RemoteImageFallback.Show,
            contentDescription = contentDescription,
            modifier =
                Modifier
                    .fillMaxSize()
                    .clip(RoundedCornerShape(12.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.55f), RoundedCornerShape(12.dp)),
        )
    }
}

@Composable
private fun ShowTicketSummary(
    show: ShowDetail,
    ticketOutboundUrl: String?,
    onVenue: () -> Unit,
    onCalendar: () -> Unit,
    onTickets: (String) -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .border(
                    width = 1.dp,
                    color = LaughTrackColors.TicketBorder,
                    shape = RoundedCornerShape(18.dp),
                ),
        color = LaughTrackColors.TicketPaper,
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            TicketFactRow(
                label = "When",
                value = formatShowDateTime(show.date, show.venueTimezone()),
                icon = "▦",
                onClick = onCalendar,
                trailing = "›",
            )
            TicketDivider()
            TicketFactRow(
                label = "Venue",
                value = show.club.name,
                icon = "▥",
                onClick = onVenue,
                trailing = "›",
            )
            show.distanceMiles?.let { distance ->
                TicketDivider()
                TicketFactRow(
                    label = "Distance",
                    value = distance.stripTrailingZeros().toPlainString() + " miles away",
                    icon = "⌖",
                )
            }
            TicketPerforation()
            TicketFactRow(
                label = "Tickets",
                value = if (showDetailIsOpenMic(show)) "RSVP" else show.ticketSummary(),
                icon = "▤",
                trailingContent = {
                    if (!show.cta.isSoldOut && ticketOutboundUrl != null) {
                        Button(
                            onClick = { onTickets(ticketOutboundUrl) },
                            colors =
                                ButtonDefaults.buttonColors(
                                    containerColor = LaughTrackColors.AccentStrong,
                                    contentColor = Color.White,
                                ),
                            shape = RoundedCornerShape(999.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                        ) {
                            Text(
                                if (showDetailIsOpenMic(show)) "RSVP ↗" else "BUY TICKETS ↗",
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black),
                            )
                        }
                    } else {
                        Text(
                            if (show.cta.isSoldOut) "SOLD OUT" else show.cta.label.uppercase(),
                            style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
                            color = LaughTrackColors.TicketInkMuted,
                        )
                    }
                },
            )
        }
    }
}

@Composable
private fun TicketFactRow(
    label: String,
    value: String,
    icon: String,
    onClick: (() -> Unit)? = null,
    trailing: String? = null,
    trailingContent: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
                .padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            modifier = Modifier.size(36.dp),
            shape = CircleShape,
            color = LaughTrackColors.TicketStub,
            contentColor = LaughTrackColors.AccentStrong,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(icon, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Black))
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                label.uppercase(),
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = LaughTrackColors.TicketInkMuted,
            )
            Text(
                value,
                style =
                    MaterialTheme.typography.titleMedium.copy(
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        fontSize = 17.sp,
                        lineHeight = 20.sp,
                    ),
                color = LaughTrackColors.TicketInk,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        trailingContent?.invoke()
        trailing?.let {
            Text(it, style = MaterialTheme.typography.headlineMedium, color = LaughTrackColors.TicketInkMuted)
        }
    }
}

@Composable
private fun TicketDivider() {
    Box(
        Modifier
            .fillMaxWidth()
            .padding(start = 50.dp)
            .height(1.dp)
            .background(LaughTrackColors.TicketBorder),
    )
}

@Composable
private fun TicketPerforation() {
    Box(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp)
            .height(1.dp)
            .background(LaughTrackColors.TicketBorder),
    )
}

@Composable
private fun ShowLineupSection(
    lineup: List<ComedianLineup>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (lineup.isEmpty()) return
    DetailDarkCard(eyebrow = "ON THE BILL", title = "Lineup") {
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            contentPadding = PaddingValues(horizontal = 2.dp),
        ) {
            items(lineup, key = { it.id }) { item ->
                LineupMarqueeCard(
                    item = item,
                    onClick = { onOpenEntity(AppRoute.ComedianDetail(item.id)) },
                )
            }
        }
    }
}

@Composable
private fun LineupMarqueeCard(
    item: ComedianLineup,
    onClick: () -> Unit,
) {
    Column(
        modifier =
            Modifier
                .width(116.dp)
                .clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            modifier =
                Modifier
                    .size(94.dp)
                    .border(2.dp, LaughTrackColors.AccentStrong, RoundedCornerShape(12.dp))
                    .padding(5.dp),
        ) {
            RemoteImage(
                url = item.imageUrl,
                fallback = RemoteImageFallback.Comedian,
                contentDescription = item.name,
                modifier =
                    Modifier
                        .fillMaxSize()
                        .clip(RoundedCornerShape(8.dp)),
            )
        }
        Text(
            item.name,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
            color = LaughTrackColors.Foreground,
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        showLineupRoleBadge(item)?.let { role ->
            Text(
                role.uppercase(),
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                color = LaughTrackColors.AccentStrong,
                textAlign = TextAlign.Center,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun RelatedShowsSection(
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (shows.isEmpty()) return
    DetailDarkCard(eyebrow = "MORE SHOWS", title = "More at this venue") {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            shows.forEach { show ->
                val (title, subtitle) = showRowTitleSubtitle(show.name, show.clubName, show.clubCity)
                TicketShowRow(
                    title = title,
                    subtitle = subtitle,
                    imageUrl = show.imageUrl,
                    dateParts = ticketStubDateParts(isoDateTime = show.date, timezone = show.timezone),
                    priceLabel = formatTicketPriceLabel(show.tickets, show.soldOut),
                    onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
                )
            }
        }
    }
}

@Composable
private fun DetailDarkCard(
    eyebrow: String,
    title: String,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text(
                eyebrow,
                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.AccentStrong,
            )
            Text(
                title,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
            )
            content()
        }
    }
}

@Composable
private fun FloatingChromeButton(
    onClick: () -> Unit,
    enabled: Boolean = true,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .size(42.dp)
                .clip(CircleShape)
                .clickable(enabled = enabled, onClick = onClick)
                .border(1.dp, LaughTrackColors.BorderSubtle, CircleShape),
        color = LaughTrackColors.Surface.copy(alpha = 0.94f),
        contentColor = if (enabled) LaughTrackColors.Foreground else LaughTrackColors.ForegroundMuted,
        shape = CircleShape,
    ) {
        Box(contentAlignment = Alignment.Center) {
            content()
        }
    }
}

private fun ShowDetail.venueTimezone(): String? = timezone ?: club.timezone

internal fun showDetailSavedActionVisible(
    show: ShowDetail,
    isSaved: Boolean,
    now: Instant = Instant.now(),
): Boolean {
    if (isSaved) return true
    val showInstant = parseShowDateTime(show.date, show.venueTimezone())?.toInstant() ?: return true
    return showInstant.isAfter(now)
}

internal fun showDetailHeroComedian(show: ShowDetail): ComedianLineup? {
    if (showDetailIsOpenMic(show)) return null
    return show.lineup
        .orEmpty()
        .firstOrNull { it.imageUrl.isNotBlank() }
}

internal fun showDetailHeroImageUrl(show: ShowDetail): String? =
    showDetailHeroComedian(show)?.imageUrl?.takeIf { it.isNotBlank() }
        ?: show.imageUrl.takeIf { it.isNotBlank() }
        ?: show.club.imageUrl.takeIf { it.isNotBlank() }

internal fun showDetailIsOpenMic(show: ShowDetail): Boolean =
    show.name.orEmpty().contains("open mic", ignoreCase = true) ||
        show.tags.orEmpty().any { tag ->
            tag.slug.contains("open-mic", ignoreCase = true) ||
                tag.name.contains("open mic", ignoreCase = true)
        }

internal fun showDetailDisplayTitle(show: ShowDetail): String {
    val title = show.name?.trim().orEmpty()
    if (title.isEmpty()) return showDetailFallbackTitle(show.club.name)

    val lineup = show.lineup.orEmpty()
    if (lineup.size == 1) {
        val comedian = lineup.single()
        val lineupNames = listOfNotNull(comedian.name, comedian.parentComedian?.name)
        if (lineupNames.any { it.trim().equals(title, ignoreCase = true) }) {
            return "$title Headlines"
        }
    }

    val showWords =
        listOf(
            "comedy",
            "show",
            "showcase",
            "friends",
            "night",
            "live",
            "open",
            "mic",
            "late",
            "early",
            "set",
            "presents",
            "special",
            "festival",
        )
    val looksLikeShowTitle = showWords.any { title.contains(it, ignoreCase = true) }
    val words = title.split(Regex("\\s+")).filter { it.isNotEmpty() }
    val looksLikePerformer =
        !looksLikeShowTitle &&
            words.size in 2..3 &&
            words.all { Regex("^[A-Z][A-Za-z.'-]*$").matches(it) }
    return if (looksLikePerformer) showDetailFallbackTitle(show.club.name) else title
}

private fun showDetailFallbackTitle(clubName: String?): String =
    clubName?.trim()?.takeIf { it.isNotEmpty() }?.let { "Comedy Show at $it" } ?: "Comedy show"

internal fun showLineupRoleBadge(comedian: ComedianLineup): String? = comedian.role?.trim()?.takeIf { it.isNotEmpty() }

private fun ShowDetail.ticketSummary(): String {
    if (cta.isSoldOut || soldOut == true) return "Sold out"
    val price =
        tickets
            .orEmpty()
            .asSequence()
            .filter { it.soldOut != true }
            .mapNotNull { it.price }
            .minOrNull()
    return price?.asMoney() ?: "Available"
}

private fun BigDecimal.asMoney(): String =
    if (compareTo(BigDecimal.ZERO) == 0) {
        "Free"
    } else {
        "$" + setScale(2, java.math.RoundingMode.HALF_UP).toPlainString()
    }
