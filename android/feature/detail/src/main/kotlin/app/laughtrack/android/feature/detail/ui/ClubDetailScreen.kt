package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Home
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
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.core.network.generated.model.ClubHighlights
import app.laughtrack.android.core.network.generated.model.ClubRelatedVenue
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.TonightHeroCard
import app.laughtrack.android.core.ui.components.TonightHeroCardContent
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import app.laughtrack.android.feature.detail.ui.components.AdaptiveDetailCatalogLayout
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.util.formatTicketPriceLabel
import app.laughtrack.android.feature.detail.util.openMap
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.parseShowDateTime
import java.math.BigDecimal
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.time.format.TextStyle
import java.util.Locale

private val CalendarCard = Color(0xFF302C28)
private val ClubBulb = Color(0xFFFFC73D)
private val ProminentTicketPaper = Color(0xFFF5E3B3)
private val ProminentTicketStub = Color(0xFFE0C27D)
private val ProminentTicketBorder = Color(0xC7963B1A)
private val ProminentTicketAccent = Color(0xFFA13D14)
private val ClubMarqueePaper = Color(0xFFFFF9E8)
private val ClubMarqueeInk = Color.Black

@Composable
fun ClubDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onHome: (() -> Unit)? = null,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: ClubDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val isLoadingMore by viewModel.isLoadingMore.collectAsStateWithLifecycle()
    val highlights by viewModel.highlights.collectAsStateWithLifecycle()
    val favoritesSnapshot by viewModel.favoritesSnapshot.collectAsStateWithLifecycle()

    Box(Modifier.fillMaxSize()) {
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success -> {
                val ui = (state as UiState.Success<ClubDetailUi>).value
                ClubDetailBody(
                    ui = ui,
                    highlights = highlights,
                    isFavorite = favoritesSnapshot.clubValues[ui.detail.id] == true,
                    isFavoritePending = viewModel.isFavoritePending(ui.detail.id),
                    isLoadingMore = isLoadingMore,
                    onFavorite = { viewModel.toggleFavorite(ui.detail.id) },
                    onLoadMore = viewModel::loadMore,
                    onBack = onBack,
                    onHome = onHome,
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
    highlights: ClubHighlights?,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    isLoadingMore: Boolean,
    onFavorite: () -> Unit,
    onLoadMore: () -> Unit,
    onBack: () -> Unit,
    onHome: (() -> Unit)?,
    onOpenEntity: (AppRoute) -> Unit,
) {
    val scrollState = rememberScrollState()
    val marqueeSummary = clubMarqueeSummary(highlights)
    var calendarFilter by remember(ui.detail.id) { mutableStateOf(ClubCalendarFilter.AnyDate) }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(bottom = 28.dp),
    ) {
        AdaptiveDetailCatalogLayout(
            hero = {
                ClubMarqueeHero(
                    club = ui.detail,
                    marqueeSummary = marqueeSummary,
                    isFavorite = isFavorite,
                    isFavoritePending = isFavoritePending,
                    onFavorite = onFavorite,
                    onBack = onBack,
                    onHome = onHome,
                )
            },
            content = {
                Column {
                    ClubHighlightsSections(
                        club = ui.detail,
                        highlights = highlights,
                        onOpenEntity = onOpenEntity,
                    )
                    ClubCalendarSection(
                        club = ui.detail,
                        shows = ui.upcomingShows,
                        totalShows = ui.totalShows,
                        canLoadMore = ui.canLoadMore,
                        isLoadingMore = isLoadingMore,
                        onLoadMore = onLoadMore,
                        onOpenEntity = onOpenEntity,
                        filter = calendarFilter,
                        onFilter = { calendarFilter = it },
                    )
                    ClubRelatedVenuesSection(
                        venues = ui.detail.relatedVenues.orEmpty(),
                        onOpenEntity = onOpenEntity,
                    )
                    val performers = clubFrequentPerformers(highlights)
                    if (performers.isNotEmpty()) {
                        ClubFrequentPerformersSection(
                            performers = performers,
                            onPerformer = { onOpenEntity(AppRoute.ComedianDetail(it.id)) },
                        )
                    }
                }
            },
        )
    }
}

internal data class ClubFeaturedShow(
    val eyebrow: String,
    val show: Show,
)

internal data class ClubMarqueePerformer(
    val name: String,
    val localizedStartTime: String,
)

internal data class ClubMarqueeSummary(
    val performers: List<ClubMarqueePerformer>,
)

private data class ClubMarqueeCandidate(
    val comedian: ComedianLineup,
    val earliestShow: Show,
)

internal fun clubMarqueeSummary(highlights: ClubHighlights?): ClubMarqueeSummary? {
    val tonightShows = highlights?.tonightShows.orEmpty()
    if (tonightShows.isEmpty()) return null

    val chronologicalShows = tonightShows.sortedWith(Comparator(::compareClubMarqueeShows))
    val performersById = mutableMapOf<Int, ClubMarqueeCandidate>()
    chronologicalShows.forEach { show ->
        show.lineup.orEmpty()
            .map(::effectiveClubShowComedian)
            .filter { it.name.isNotBlank() }
            .forEach { comedian ->
                val existing = performersById[comedian.id]
                if (existing == null) {
                    performersById[comedian.id] = ClubMarqueeCandidate(comedian, show)
                } else if (clubMarqueePerformerRanking.compare(comedian, existing.comedian) < 0) {
                    performersById[comedian.id] = existing.copy(comedian = comedian)
                }
            }
    }
    val performers =
        performersById.values
            .sortedWith { left, right ->
                clubMarqueePerformerRanking.compare(left.comedian, right.comedian)
            }
            .take(3)
            .map { candidate ->
                ClubMarqueePerformer(
                    name = candidate.comedian.name.trim(),
                    localizedStartTime = clubMarqueeStartTime(candidate.earliestShow),
                )
            }
            .ifEmpty {
                listOf(
                    ClubMarqueePerformer(
                        name =
                            chronologicalShows.first().name
                                ?.trim()
                                ?.takeIf(String::isNotEmpty)
                                ?: "Show",
                        localizedStartTime = clubMarqueeStartTime(chronologicalShows.first()),
                    ),
                )
            }

    return ClubMarqueeSummary(performers = performers)
}

internal fun clubNextFeaturedShow(highlights: ClubHighlights?): ClubFeaturedShow? =
    highlights
        ?.takeIf { it.tonightShows.isEmpty() }
        ?.nextShow
        ?.let { ClubFeaturedShow("Next up", it) }

private val clubMarqueePerformerRanking =
    compareByDescending<ComedianLineup> {
        it.socialData?.popularity ?: BigDecimal.valueOf(-1)
    }
        .thenByDescending { it.showCount ?: 0 }
        .thenBy { it.id }

private fun clubMarqueeStartTime(show: Show): String =
    parseShowDateTime(show.date, show.timezone)
        ?.toLocalTime()
        ?.format(DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(Locale.getDefault()))
        .orEmpty()

private fun compareClubMarqueeShows(
    left: Show,
    right: Show,
): Int {
    val leftInstant = parseShowDateTime(left.date, left.timezone)?.toInstant()
    val rightInstant = parseShowDateTime(right.date, right.timezone)?.toInstant()
    val timeComparison =
        when {
            leftInstant == null && rightInstant == null -> 0
            leftInstant == null -> 1
            rightInstant == null -> -1
            else -> leftInstant.compareTo(rightInstant)
        }
    return timeComparison.takeIf { it != 0 } ?: left.id.compareTo(right.id)
}

internal fun clubFrequentPerformers(highlights: ClubHighlights?): List<ComedianListItem> =
    highlights?.frequentPerformers.orEmpty()

@Composable
private fun ClubHighlightsSections(
    club: ClubDetail,
    highlights: ClubHighlights?,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (clubMarqueeSummary(highlights) == null) {
        clubNextFeaturedShow(highlights)?.let { featured ->
            ClubFeaturedShowSection(
                club = club,
                featured = featured,
                onClick = { onOpenEntity(AppRoute.ShowDetail(featured.show.id)) },
            )
        }
    }
}

@Composable
private fun ClubTonightMarqueeSection(
    club: ClubDetail,
    summary: ClubMarqueeSummary,
) {
    Surface(
        color = ClubMarqueePaper,
        contentColor = ClubMarqueeInk,
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, ClubMarqueeInk.copy(alpha = 0.72f)),
        modifier =
            Modifier
                .fillMaxWidth()
                .testTag(CLUB_HIGHLIGHT_SECTION_TEST_TAG)
                .semantics { contentDescription = "Show marquee at ${club.name}" },
    ) {
        Box {
            Column(Modifier.padding(8.dp)) {
                Surface(
                    color = ClubMarqueeInk,
                    contentColor = ClubMarqueePaper,
                    shape = RoundedCornerShape(999.dp),
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                ) {
                    Text(
                        "TONIGHT",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black),
                        letterSpacing = 1.2.sp,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 4.dp),
                    )
                }
                summary.performers.forEachIndexed { index, performer ->
                    if (index > 0) {
                        Box(
                            Modifier
                                .fillMaxWidth()
                                .height(1.dp)
                                .background(ClubMarqueeInk.copy(alpha = 0.24f)),
                        )
                    }
                    Row(
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 10.dp, vertical = 15.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            performer.name.uppercase(Locale.getDefault()),
                            style =
                                MaterialTheme.typography.titleMedium.copy(
                                    fontWeight = FontWeight.Black,
                                    letterSpacing = 0.8.sp,
                                ),
                            color = Color.Black,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            performer.localizedStartTime.uppercase(Locale.getDefault()),
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = ClubMarqueeInk.copy(alpha = 0.68f),
                            maxLines = 1,
                        )
                    }
                }
            }
            Canvas(Modifier.fillMaxSize()) {
                val inset = 7.dp.toPx()
                val dotRadius = 1.5.dp.toPx()
                val step = 12.dp.toPx()
                val left = inset
                val top = inset
                val right = size.width - inset
                val bottom = size.height - inset

                var x = left + step
                while (x < right - step) {
                    drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(x, top))
                    drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(x, bottom))
                    x += step
                }
                var y = top + step
                while (y < bottom - step) {
                    drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(left, y))
                    drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(right, y))
                    y += step
                }
            }
        }
    }
}

@Composable
private fun ClubFeaturedShowSection(
    club: ClubDetail,
    featured: ClubFeaturedShow,
    onClick: () -> Unit,
) {
    val show = featured.show
    val headliner = clubShowHeadliner(show)
    val time =
        parseShowDateTime(show.date, show.timezone)?.toLocalTime()
            ?.format(java.time.format.DateTimeFormatter.ofPattern("h:mm a", Locale.US))
            .orEmpty()
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .testTag(CLUB_HIGHLIGHT_SECTION_TEST_TAG)
                .semantics { contentDescription = "${featured.eyebrow} show at ${club.name}" }
                .padding(horizontal = 8.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            featured.eyebrow.uppercase(Locale.US),
            style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
            color = LaughTrackColors.AccentStrong,
        )
        Surface(
            color = LaughTrackColors.Surface,
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth().height(388.dp),
        ) {
            TonightHeroCard(
                content =
                    TonightHeroCardContent(
                        timeLabel = time,
                        title = show.name ?: "Show",
                        venueLabel = "At ${show.clubName ?: club.name}",
                        artworkUrl = headliner?.imageUrl ?: show.imageUrl.takeIf(String::isNotBlank),
                        artworkCaption = headliner?.name ?: show.name ?: club.name,
                        artworkContentDescription = headliner?.name ?: show.name ?: "Show",
                        artworkFallback =
                            if (headliner != null) {
                                RemoteImageFallback.Comedian
                            } else {
                                RemoteImageFallback.Show
                            },
                        priceLabel = clubShowTicketLabel(show),
                    ),
                onClick = onClick,
                modifier =
                    Modifier
                        .fillMaxSize()
                        .testTag("$CLUB_HIGHLIGHT_SHOW_TEST_TAG_PREFIX${show.id}")
                        .semantics { contentDescription = "Open ${show.name ?: "show"}" }
                        .padding(12.dp),
                artworkHeight = 170.dp,
            )
        }
    }
}

@Composable
private fun ClubFrequentPerformersSection(
    performers: List<ComedianListItem>,
    onPerformer: (ComedianListItem) -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .testTag(CLUB_FREQUENT_PERFORMERS_SECTION_TEST_TAG)
                .semantics { contentDescription = "Frequent performers" }
                .padding(horizontal = 8.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "Frequently on this stage",
            style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
            color = LaughTrackColors.AccentStrong,
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(performers, key = { it.uuid }) { performer ->
                Surface(
                    modifier =
                        Modifier
                            .width(148.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .testTag("$CLUB_PERFORMER_TEST_TAG_PREFIX${performer.id}")
                            .semantics { contentDescription = "Open ${performer.name}" }
                            .clickable(role = Role.Button) { onPerformer(performer) },
                    color = LaughTrackColors.Surface,
                    shape = RoundedCornerShape(14.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
                ) {
                    Column {
                        RemoteImage(
                            url = performer.imageUrl,
                            fallback = RemoteImageFallback.Comedian,
                            contentDescription = null,
                            modifier = Modifier.fillMaxWidth().height(116.dp),
                        )
                        Text(
                            performer.name,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            color = LaughTrackColors.Foreground,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(10.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ClubMarqueeHero(
    club: ClubDetail,
    marqueeSummary: ClubMarqueeSummary?,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onBack: () -> Unit,
    onHome: (() -> Unit)?,
) {
    val context = LocalContext.current
    BoxWithConstraints(
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
        val contentTopPadding = if (maxWidth <= 360.dp) 148.dp else 118.dp
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ClubChromeButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
                onHome?.let {
                    ClubChromeButton(onClick = it) {
                        Icon(Icons.Filled.Home, contentDescription = "Home")
                    }
                }
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
                    .padding(top = contentTopPadding, start = 20.dp, end = 20.dp, bottom = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                club.name.uppercase(),
                style =
                    MaterialTheme.typography.headlineMedium.copy(
                        fontWeight = FontWeight.Black,
                        fontSize = 24.sp,
                        lineHeight = 30.sp,
                        letterSpacing = 0.4.sp,
                    ),
                color = LaughTrackColors.Foreground,
                textAlign = TextAlign.Center,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ClubHeroAction(label = "Website", symbol = "↗", onClick = { context.openUrl(club.website) })
                ClubHeroAction(label = "Directions", symbol = "▥", onClick = { context.openMap(club.address) })
            }
            ClubPoster(url = club.heroImageUrl.ifBlank { club.imageUrl }, contentDescription = club.name)
            marqueeSummary?.let { summary ->
                ClubTonightMarqueeSection(
                    club = club,
                    summary = summary,
                )
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
                .size(206.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(ClubMarqueePaper)
                .border(1.5.dp, ClubMarqueeInk.copy(alpha = 0.72f), RoundedCornerShape(12.dp)),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val cornerRadius = 20.dp.toPx()
            val dotRadius = 1.5.dp.toPx()
            val inset = 7.dp.toPx()
            val left = inset
            val top = inset
            val right = size.width - inset
            val bottom = size.height - inset
            val step = 11.dp.toPx()

            drawRoundRect(
                color = ClubMarqueeInk.copy(alpha = 0.22f),
                topLeft = Offset(left, top),
                size = Size(right - left, bottom - top),
                cornerRadius = CornerRadius(cornerRadius, cornerRadius),
                style = Stroke(width = 1.dp.toPx()),
            )

            var x = left + cornerRadius
            while (x <= right - cornerRadius) {
                drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(x, top))
                drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(x, bottom))
                x += step
            }

            var y = top + cornerRadius
            while (y <= bottom - cornerRadius) {
                drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(left, y))
                drawCircle(ClubBulb.copy(alpha = 0.42f), dotRadius, Offset(right, y))
                y += step
            }
        }
        RemoteImage(
            url = url,
            fallback = RemoteImageFallback.Club,
            contentDescription = contentDescription,
            contentScale = ContentScale.Fit,
            modifier =
                Modifier
                    .padding(10.dp)
                    .fillMaxSize()
                    .clip(RoundedCornerShape(8.dp))
                    .border(1.dp, ClubMarqueeInk.copy(alpha = 0.55f), RoundedCornerShape(8.dp)),
        )
    }
}

@Composable
private fun ClubHeroAction(
    label: String,
    symbol: String,
    onClick: () -> Unit,
) {
    Surface(
        color = ClubMarqueeInk.copy(alpha = 0.82f),
        contentColor = ClubMarqueePaper,
        shape = RoundedCornerShape(999.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, ClubMarqueePaper.copy(alpha = 0.42f)),
        modifier =
            Modifier
                .heightIn(min = 48.dp)
                .semantics { contentDescription = label }
                .clickable(role = Role.Button, onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(symbol, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Black))
            Text(label, style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold))
        }
    }
}

@Composable
private fun ClubCalendarSection(
    club: ClubDetail,
    shows: List<Show>,
    totalShows: Int,
    canLoadMore: Boolean,
    isLoadingMore: Boolean,
    onLoadMore: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    filter: ClubCalendarFilter,
    onFilter: (ClubCalendarFilter) -> Unit,
    modifier: Modifier = Modifier,
) {
    val visibleShows = clubCalendarShows(shows, filter)
    Column(
        modifier
            .fillMaxWidth()
            .testTag(CLUB_CALENDAR_SECTION_TEST_TAG)
            .padding(horizontal = 8.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
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
                modifier =
                    Modifier
                        .testTag(CLUB_CALENDAR_DATE_FILTER_TEST_TAG)
                        .clickable(role = Role.Button) {
                            onFilter(
                                if (filter == ClubCalendarFilter.Today) {
                                    ClubCalendarFilter.AnyDate
                                } else {
                                    ClubCalendarFilter.Today
                                },
                            )
                        },
            ) {
                Text(
                    if (filter == ClubCalendarFilter.Today) "▦  Today" else "▦  Any date",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                )
            }
        }

        Text(
            if (filter == ClubCalendarFilter.Today) {
                "Showing ${visibleShows.size} today"
            } else {
                "Showing ${shows.size} of $totalShows"
            },
            style = MaterialTheme.typography.titleSmall,
            color = LaughTrackColors.ForegroundMuted,
        )

        if (visibleShows.isEmpty()) {
            Text(
                if (filter == ClubCalendarFilter.Today) "No shows today." else "No upcoming shows yet.",
                style = MaterialTheme.typography.bodyMedium,
                color = LaughTrackColors.ForegroundMuted,
            )
        } else {
            val standoutShowId = clubShowStandoutId(visibleShows)
            visibleShows.forEach { show ->
                ClubShowCard(
                    club = club,
                    show = show,
                    prominent = show.id == standoutShowId,
                    onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
                )
            }
        }

        if (canLoadMore) {
            Surface(
                modifier = Modifier.fillMaxWidth().clickable(enabled = !isLoadingMore, onClick = onLoadMore),
                color = LaughTrackColors.Surface,
                contentColor = LaughTrackColors.Foreground,
                shape = RoundedCornerShape(999.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
            ) {
                Text(
                    if (isLoadingMore) "Loading…" else "Load more shows",
                    modifier = Modifier.padding(horizontal = 18.dp, vertical = 12.dp),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
    }
}

@Composable
private fun ClubShowCard(
    club: ClubDetail,
    show: Show,
    prominent: Boolean,
    onClick: () -> Unit,
) {
    val date = show.dateParts()
    val headliner = clubShowHeadliner(show)
    val supporting = clubShowSupportingLineup(show, excluding = headliner)
    val paper = if (prominent) ProminentTicketPaper else LaughTrackColors.TicketPaper
    val stub = if (prominent) ProminentTicketStub else LaughTrackColors.TicketStub
    val border = if (prominent) ProminentTicketBorder else LaughTrackColors.TicketBorder
    val accent = if (prominent) ProminentTicketAccent else LaughTrackColors.TicketAccent
    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .testTag(CLUB_SHOW_ROW_TEST_TAG)
                .clip(RoundedCornerShape(18.dp))
                .clickable(onClick = onClick),
        color = paper,
        shape = RoundedCornerShape(18.dp),
        border = androidx.compose.foundation.BorderStroke(if (prominent) 1.5.dp else 1.dp, border),
    ) {
        Box {
            Row(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(IntrinsicSize.Min)
                        .heightIn(min = 120.dp),
            ) {
                Column(
                    modifier =
                        Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .background(
                                Brush.linearGradient(
                                    colors =
                                        listOf(
                                            Color.White.copy(alpha = if (prominent) 0.30f else 0.24f),
                                            LaughTrackColors.AccentStrong.copy(alpha = if (prominent) 0.13f else 0.10f),
                                            Color.Black.copy(alpha = 0.03f),
                                        ),
                                ),
                            )
                            .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RemoteImage(
                            url = headliner?.imageUrl ?: show.imageUrl.takeIf { it.isNotBlank() },
                            fallback =
                                if (headliner != null) {
                                    RemoteImageFallback.Comedian
                                } else {
                                    RemoteImageFallback.Show
                                },
                            contentDescription = headliner?.name ?: show.name,
                            modifier =
                                Modifier
                                    .size(60.dp)
                                    .clip(CircleShape)
                                    .border(1.5.dp, accent.copy(alpha = 0.5f), CircleShape),
                        )
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                headliner?.name ?: show.name ?: "Show",
                                style =
                                    MaterialTheme.typography.titleMedium.copy(
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 18.sp,
                                    ),
                                color = LaughTrackColors.TicketInk,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                clubShowVenueLine(club, show),
                                style = MaterialTheme.typography.bodySmall,
                                color = LaughTrackColors.TicketInkMuted,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                    if (supporting.isNotEmpty()) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Row(horizontalArrangement = Arrangement.spacedBy((-8).dp)) {
                                supporting.forEach { comedian ->
                                    RemoteImage(
                                        url = comedian.imageUrl,
                                        fallback = RemoteImageFallback.Comedian,
                                        contentDescription = comedian.name,
                                        modifier =
                                            Modifier
                                                .size(26.dp)
                                                .clip(CircleShape)
                                                .border(1.dp, paper, CircleShape),
                                    )
                                }
                            }
                            Text(
                                "with ${supporting.joinToString(", ") { it.name }}",
                                style = MaterialTheme.typography.bodySmall,
                                color = LaughTrackColors.TicketInkMuted,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }

                ClubTicketPerforation(border)

                Column(
                    modifier =
                        Modifier
                            .width(88.dp)
                            .fillMaxHeight()
                            .background(stub)
                            .padding(vertical = 8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        date.weekday,
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black),
                        color = accent,
                        letterSpacing = 1.4.sp,
                    )
                    Text(
                        date.day,
                        style =
                            MaterialTheme.typography.headlineLarge.copy(
                                fontWeight = FontWeight.Black,
                                fontSize = 26.sp,
                            ),
                        color = LaughTrackColors.TicketInk,
                    )
                    Text(
                        date.month,
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black),
                        color = LaughTrackColors.TicketInkMuted,
                        letterSpacing = 1.2.sp,
                    )
                    Text(
                        date.time,
                        style = MaterialTheme.typography.labelMedium,
                        color = LaughTrackColors.TicketInkMuted,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                    clubShowTicketLabel(show)?.let { price ->
                        Text(
                            price,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Black),
                            color = accent,
                        )
                    }
                }
            }
            if (prominent) {
                Box(Modifier.fillMaxHeight().width(4.dp).background(ProminentTicketAccent.copy(alpha = 0.9f)))
            }
        }
    }
}

@Composable
private fun ClubTicketPerforation(color: Color) {
    Canvas(
        Modifier
            .width(1.dp)
            .fillMaxHeight()
            .padding(vertical = 8.dp),
    ) {
        drawLine(
            color = color.copy(alpha = 0.6f),
            start = Offset(size.width / 2, 0f),
            end = Offset(size.width / 2, size.height),
            strokeWidth = 1.dp.toPx(),
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(3.dp.toPx(), 3.dp.toPx())),
        )
    }
}

/** Stable semantics hook used to mirror the iOS club-detail → show-detail screenshot flow. */
const val CLUB_SHOW_ROW_TEST_TAG = "club-show-row"
const val CLUB_HIGHLIGHT_SECTION_TEST_TAG = "club-detail-highlight-section"
const val CLUB_HIGHLIGHT_SHOW_TEST_TAG_PREFIX = "club-detail-highlight-show-"
const val CLUB_CALENDAR_SECTION_TEST_TAG = "club-calendar-section"
const val CLUB_CALENDAR_DATE_FILTER_TEST_TAG = "club-calendar-date-filter"
const val CLUB_FREQUENT_PERFORMERS_SECTION_TEST_TAG = "club-detail-frequent-performers-section"
const val CLUB_PERFORMER_TEST_TAG_PREFIX = "club-detail-performer-"

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
                        fallback = RemoteImageFallback.Club,
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
                .size(40.dp)
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

internal enum class ClubCalendarFilter {
    AnyDate,
    Today,
}

internal fun clubCalendarShows(
    shows: List<Show>,
    filter: ClubCalendarFilter,
    now: Instant = Instant.now(),
): List<Show> {
    if (filter == ClubCalendarFilter.AnyDate) return shows
    return shows.filter { show ->
        val showDateTime = parseShowDateTime(show.date, show.timezone) ?: return@filter false
        showDateTime.toLocalDate() == now.atZone(showDateTime.zone).toLocalDate()
    }
}

private fun Show.dateParts(): ClubShowDateParts {
    val parsed = parseShowDateTime(date, timezone)
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

internal fun clubShowHeadliner(show: Show): ComedianLineup? {
    val featured =
        show.lineup
            .orEmpty()
            .map(::effectiveClubShowComedian)
            .maxByOrNull { it.showCount ?: 0 }
    return featured?.takeIf { it.imageUrl.isNotBlank() }
}

internal fun clubShowSupportingLineup(
    show: Show,
    excluding: ComedianLineup?,
): List<ComedianLineup> {
    val lineup = show.lineup.orEmpty().map(::effectiveClubShowComedian)
    val filtered = lineup.filter { excluding == null || it.id != excluding.id }
    val ordered =
        if (filtered.any { it.showCount != null }) {
            filtered.sortedByDescending { it.showCount ?: 0 }
        } else {
            filtered
        }
    return ordered.distinctBy { it.id }.take(3)
}

internal fun clubShowStandoutId(shows: List<Show>): Int? {
    val scored =
        shows.mapNotNull { show ->
            show.popularityScore?.takeIf { it.signum() > 0 }?.let { show.id to it }
        }
    val topScore = scored.maxOfOrNull { it.second } ?: return null
    return scored.singleOrNull { it.second.compareTo(topScore) == 0 }?.first
}

internal fun clubShowVenueLine(
    club: ClubDetail,
    show: Show,
): String {
    val location =
        listOfNotNull(
            show.clubCity?.trim()?.takeIf(String::isNotEmpty),
            show.clubState?.trim()?.takeIf(String::isNotEmpty),
        )
    return if (location.isEmpty()) club.name else "${club.name} • ${location.joinToString(", ")}"
}

internal fun clubShowTicketLabel(show: Show): String? = show.ticketLabel()?.replace(Regex("\\.00(?=$|\\s)"), "")

private fun effectiveClubShowComedian(comedian: ComedianLineup): ComedianLineup = comedian.parentComedian ?: comedian

private fun Show.ticketLabel(): String? = formatTicketPriceLabel(tickets, soldOut)
