package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.core.network.generated.model.ClubRelatedVenue
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.util.openMap
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.parseShowDateTime
import java.math.BigDecimal
import java.time.format.TextStyle
import java.util.Locale

private val CalendarCard = Color(0xFF302C28)

@Composable
fun ClubDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: ClubDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val favoritesSnapshot by viewModel.favoritesSnapshot.collectAsStateWithLifecycle()

    Box(
        Modifier
            .fillMaxSize()
            .background(LaughTrackColors.Canvas),
    ) {
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success -> {
                val ui = (state as UiState.Success<ClubDetailUi>).value
                ClubDetailBody(
                    ui = ui,
                    isFavorite = favoritesSnapshot.clubValues[ui.detail.id] == true,
                    isFavoritePending = viewModel.isFavoritePending(ui.detail.id),
                    onFavorite = { viewModel.toggleFavorite(ui.detail.id) },
                    onBack = onBack,
                    onOpenEntity = onOpenEntity,
                )
            }
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun ClubDetailBody(
    ui: ClubDetailUi,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 28.dp),
    ) {
        ClubMarqueeHero(
            club = ui.detail,
            isFavorite = isFavorite,
            isFavoritePending = isFavoritePending,
            onFavorite = onFavorite,
            onBack = onBack,
        )
        ClubCalendarSection(club = ui.detail, shows = ui.upcomingShows, onOpenEntity = onOpenEntity)
        ClubRelatedVenuesSection(venues = ui.detail.relatedVenues.orEmpty(), onOpenEntity = onOpenEntity)
    }
}

@Composable
private fun ClubMarqueeHero(
    club: ClubDetail,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    Box(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.radialGradient(
                    colors =
                        listOf(
                            LaughTrackColors.Highlight.copy(alpha = 0.58f),
                            LaughTrackColors.Surface.copy(alpha = 0.96f),
                            LaughTrackColors.Canvas,
                        ),
                ),
            ),
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            ClubChromeButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            ClubChromeButton(onClick = onFavorite, enabled = !isFavoritePending) {
                Icon(
                    imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                    contentDescription = if (isFavorite) "Remove favorite" else "Favorite",
                    tint = if (isFavorite) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                )
            }
        }

        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(top = 82.dp, start = 20.dp, end = 20.dp, bottom = 42.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Text(
                club.name.uppercase(),
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
                textAlign = TextAlign.Center,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            ClubPoster(url = club.heroImageUrl.ifBlank { club.imageUrl }, contentDescription = club.name)
            Row(horizontalArrangement = Arrangement.spacedBy(28.dp)) {
                ClubHeroAction(label = "Website", symbol = "↗", onClick = { context.openUrl(club.website) })
                ClubHeroAction(label = "Maps", symbol = "▥", onClick = { context.openMap(club.address) })
            }
        }
    }
}

@Composable
private fun ClubPoster(
    url: String?,
    contentDescription: String?,
) {
    Box(
        modifier =
            Modifier
                .size(214.dp)
                .padding(2.dp),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val cornerRadius = 20.dp.toPx()
            val dotRadius = 2.dp.toPx()
            val inset = 5.dp.toPx()
            val left = inset
            val top = inset
            val right = size.width - inset
            val bottom = size.height - inset
            val step = 11.dp.toPx()

            drawRoundRect(
                color = LaughTrackColors.AccentStrong.copy(alpha = 0.24f),
                topLeft = Offset(left, top),
                size = Size(right - left, bottom - top),
                cornerRadius = CornerRadius(cornerRadius, cornerRadius),
                style = Stroke(width = 1.dp.toPx()),
            )

            var x = left + cornerRadius
            while (x <= right - cornerRadius) {
                drawCircle(LaughTrackColors.AccentStrong, dotRadius, Offset(x, top))
                drawCircle(LaughTrackColors.AccentStrong, dotRadius, Offset(x, bottom))
                x += step
            }

            var y = top + cornerRadius
            while (y <= bottom - cornerRadius) {
                drawCircle(LaughTrackColors.AccentStrong, dotRadius, Offset(left, y))
                drawCircle(LaughTrackColors.AccentStrong, dotRadius, Offset(right, y))
                y += step
            }
        }
        RemoteImage(
            url = url,
            contentDescription = contentDescription,
            modifier =
                Modifier
                    .padding(15.dp)
                    .fillMaxSize()
                    .clip(RoundedCornerShape(12.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.55f), RoundedCornerShape(12.dp)),
        )
    }
}

@Composable
private fun ClubHeroAction(
    label: String,
    symbol: String,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier.clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Surface(
            modifier = Modifier.size(48.dp),
            color = LaughTrackColors.Surface.copy(alpha = 0.92f),
            contentColor = LaughTrackColors.Foreground,
            shape = CircleShape,
            border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(symbol, style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Black))
            }
        }
        Text(
            label,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
            color = LaughTrackColors.Foreground,
        )
    }
}

@Composable
private fun ClubCalendarSection(
    club: ClubDetail,
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                "CALENDAR",
                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.AccentStrong,
            )
            Text(
                "Search shows",
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
            )
            Surface(
                color = LaughTrackColors.Surface,
                contentColor = LaughTrackColors.Foreground,
                shape = RoundedCornerShape(999.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
            ) {
                Text(
                    "▦  Any date",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
                )
            }
        }

        Text(
            "Showing ${shows.size.coerceAtMost(20)} of ${shows.size}",
            style = MaterialTheme.typography.titleSmall,
            color = LaughTrackColors.ForegroundMuted,
        )

        if (shows.isEmpty()) {
            Text(
                "No upcoming shows yet.",
                style = MaterialTheme.typography.bodyMedium,
                color = LaughTrackColors.ForegroundMuted,
            )
            return@Column
        }

        shows.take(10).forEach { show ->
            ClubShowCard(
                club = club,
                show = show,
                onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
            )
        }
    }
}

@Composable
private fun ClubShowCard(
    club: ClubDetail,
    show: Show,
    onClick: () -> Unit,
) {
    val date = show.dateParts()
    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(18.dp))
                .clickable(onClick = onClick),
        color = LaughTrackColors.TicketPaper,
        shape = RoundedCornerShape(18.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.TicketBorder),
    ) {
        Row(Modifier.height(142.dp)) {
            Row(
                modifier =
                    Modifier
                        .weight(1f)
                        .padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    url = show.primaryImageUrl(),
                    contentDescription = show.name,
                    modifier =
                        Modifier
                            .size(70.dp)
                            .clip(CircleShape)
                            .border(1.dp, LaughTrackColors.TicketAccent.copy(alpha = 0.5f), CircleShape),
                )
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        show.name ?: show.lineup?.firstOrNull()?.name ?: "Show",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                        color = LaughTrackColors.TicketInk,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        club.name,
                        style = MaterialTheme.typography.titleSmall,
                        color = LaughTrackColors.TicketInkMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    show.lineupNames()?.let {
                        Text(
                            "with $it",
                            style = MaterialTheme.typography.titleSmall,
                            color = LaughTrackColors.TicketInkMuted,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            Column(
                modifier =
                    Modifier
                        .width(94.dp)
                        .fillMaxSize()
                        .background(LaughTrackColors.TicketStub)
                        .border(1.dp, LaughTrackColors.TicketBorder),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    date.weekday,
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
                    color = LaughTrackColors.TicketAccent,
                    letterSpacing = 2.sp,
                )
                Text(
                    date.day,
                    style = MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.Black),
                    color = LaughTrackColors.TicketInk,
                )
                Text(
                    date.month,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Black),
                    color = LaughTrackColors.TicketInkMuted,
                    letterSpacing = 2.sp,
                )
                Text(
                    date.time,
                    style = MaterialTheme.typography.titleSmall,
                    color = LaughTrackColors.TicketInkMuted,
                )
                Text(
                    show.ticketLabel() ?: "",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Black),
                    color = LaughTrackColors.TicketAccent,
                )
            }
        }
    }
}

@Composable
private fun ClubRelatedVenuesSection(
    venues: List<ClubRelatedVenue>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (venues.isEmpty()) return
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "Related venues",
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Black),
            color = LaughTrackColors.Foreground,
        )
        venues.forEach { venue ->
            Surface(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .clickable { onOpenEntity(AppRoute.ClubDetail(venue.id)) },
                color = CalendarCard,
                shape = RoundedCornerShape(16.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
            ) {
                Row(
                    Modifier.padding(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RemoteImage(
                        url = venue.imageUrl,
                        contentDescription = venue.name,
                        modifier =
                            Modifier
                                .size(56.dp)
                                .clip(RoundedCornerShape(10.dp)),
                    )
                    Column(Modifier.weight(1f)) {
                        Text(venue.name, color = LaughTrackColors.Foreground, fontWeight = FontWeight.Bold)
                        Text(
                            listOfNotNull(venue.city, venue.state).joinToString(", "),
                            color = LaughTrackColors.ForegroundMuted,
                        )
                    }
                    Text("›", style = MaterialTheme.typography.headlineSmall, color = LaughTrackColors.ForegroundMuted)
                }
            }
        }
    }
}

@Composable
private fun ClubChromeButton(
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

private data class ClubShowDateParts(
    val weekday: String,
    val day: String,
    val month: String,
    val time: String,
)

private fun Show.dateParts(): ClubShowDateParts {
    val parsed = parseShowDateTime(date)
    return if (parsed == null) {
        ClubShowDateParts("", "", "", "")
    } else {
        ClubShowDateParts(
            weekday = parsed.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.US).uppercase(),
            day = parsed.dayOfMonth.toString(),
            month = parsed.month.getDisplayName(TextStyle.SHORT, Locale.US).uppercase(),
            time =
                parsed.toLocalTime()
                    .format(java.time.format.DateTimeFormatter.ofPattern("h:mm a", Locale.US)),
        )
    }
}

private fun Show.primaryImageUrl(): String? =
    lineup.orEmpty().firstOrNull { it.imageUrl.isNotBlank() }?.imageUrl
        ?: imageUrl.takeIf { it.isNotBlank() }

private fun Show.lineupNames(): String? =
    lineup
        ?.drop(1)
        ?.take(4)
        ?.joinToString(", ") { it.name }
        ?.takeIf { it.isNotBlank() }

private fun Show.ticketLabel(): String? {
    if (soldOut == true) return "Sold out"
    val price =
        tickets
            .orEmpty()
            .asSequence()
            .filter { it.soldOut != true }
            .mapNotNull { it.price }
            .minOrNull()
    return price?.let {
        if (it.compareTo(BigDecimal.ZERO) == 0) {
            "Free"
        } else {
            "$" + it.setScale(2, java.math.RoundingMode.HALF_UP).toPlainString()
        }
    }
}
