@file:Suppress("FunctionName")

package app.laughtrack.android.feature.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.SearchDestination
import app.laughtrack.android.core.navigation.SearchLaunchRequest
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.SkeletonBox
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.TicketShowRowColors
import app.laughtrack.android.core.ui.components.TicketStubColors
import app.laughtrack.android.core.ui.components.TonightHeroCard
import app.laughtrack.android.core.ui.components.TonightHeroCardContent
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.ui.HomeUiState
import app.laughtrack.android.feature.home.ui.HomeViewModel
import java.time.LocalDate
import java.util.Locale

/** Stable semantics anchor for instrumented Discover scroll-restoration coverage. */
const val HOME_DISCOVER_LIST_TEST_TAG = "homeDiscoverList"

/** Discover/Home surface backed by the composite home feed endpoint. */
@Composable
fun HomeScreen(
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onOpenSearch: (SearchLaunchRequest) -> Unit,
    signedIn: Boolean = false,
    modifier: Modifier = Modifier,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

    LaunchedEffect(signedIn) {
        viewModel.onAuthStateChanged(signedIn)
    }

    Box(modifier = modifier.fillMaxSize()) {
        Box(Modifier.fillMaxSize().statusBarsPadding()) {
            when (state.feed) {
                is UiState.Failure -> HomeError(onRetry = viewModel::retry)
                is UiState.Success ->
                    HomeContent(
                        state = state,
                        listState = listState,
                        onOpenEntity = onOpenEntity,
                        onPlay = onPlay,
                        onOpenSearch = onOpenSearch,
                        onManualZip = viewModel::setManualZip,
                        onUseLocation = viewModel::useDeviceLocation,
                        onSetDistance = viewModel::setDistance,
                        onClearLocation = viewModel::clearLocation,
                        onRailSelected = viewModel::onDiscoverRailSelected,
                    )
                else -> HomeLoading()
            }
        }
    }
}

@Composable
private fun HomeContent(
    state: HomeUiState,
    listState: LazyListState,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onOpenSearch: (SearchLaunchRequest) -> Unit,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
    onSetDistance: (Int) -> Unit,
    onClearLocation: () -> Unit,
    onRailSelected: (HomeDiscoverRailAttribution) -> Unit,
    modifier: Modifier = Modifier,
) {
    val plannedRails = remember(state.loadedFeed) { resolveHomeDiscoverRails(state.loadedFeed) }
    Box(
        modifier = modifier.fillMaxSize(),
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().testTag(HOME_DISCOVER_LIST_TEST_TAG),
            state = listState,
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 12.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item(key = "discover-header") {
                DiscoverHeader(onOpenEntity = onOpenEntity)
            }
            item(key = "location") {
                LocationHeader(
                    title = state.locationTitle,
                    subtitle = state.locationSubtitle,
                    // activeZip (not the requested zip) so the sheet prefills the same
                    // ZIP the Saved ZIP subtitle reports, including the hero fallback;
                    // the requested zip separately drives the sheet's apply guard.
                    zip = state.activeZip,
                    requestedZip = state.zip,
                    hasExplicitLocation = state.hasExplicitLocation,
                    distanceMiles = state.distanceMiles,
                    isResolving = state.isResolvingLocation,
                    onManualZip = onManualZip,
                    onUseLocation = onUseLocation,
                    onSetDistance = onSetDistance,
                    onClearLocation = onClearLocation,
                )
            }
            if (plannedRails == null) {
                item(key = "tonight") {
                    ShowsTonightRail(
                        shows = state.showsTonight,
                        onOpenEntity = onOpenEntity,
                        onOpenSearch = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.TONIGHT, state)) },
                    )
                }
                item(key = "best-this-week") {
                    ShowListRail(
                        eyebrow = "Coming Up",
                        title = "Best shows this week",
                        emptyMessage = "No upcoming shows are listed near you this week.",
                        shows = state.trendingThisWeek,
                        onOpenEntity = onOpenEntity,
                        onOpenSearch = {
                            onOpenSearch(homeRailSearchRequest(HomeExpandableRail.BEST_THIS_WEEK, state))
                        },
                    )
                }
                if (state.followedComedianShows.isNotEmpty()) {
                    item(key = "followed-comedian-shows") {
                        FollowedComedianShowsRail(
                            shows = state.followedComedianShows,
                            onOpenEntity = onOpenEntity,
                        )
                    }
                }
                item(key = "comedians") {
                    ComedianRail(
                        state.comedians,
                        onOpenEntity,
                        onOpenSearch = {
                            onOpenSearch(homeRailSearchRequest(HomeExpandableRail.COMEDIANS, state))
                        },
                    )
                }
                item(key = "clubs") {
                    ClubRail(
                        state.clubs,
                        onOpenEntity,
                        onOpenSearch = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.CLUBS, state)) },
                    )
                }
                item(key = "podcasts") {
                    HomePodcastRail(
                        episodes = state.podcastEpisodes,
                        podcasts = state.podcasts,
                        onOpenEntity = onOpenEntity,
                        onPlay = onPlay,
                        onBrowsePodcasts = {
                            onOpenSearch(homeRailSearchRequest(HomeExpandableRail.PODCASTS, state))
                        },
                    )
                }
            } else {
                plannedRails.forEach { section ->
                    item(key = section.stableKey) {
                        HomeDiscoverPlannedRail(
                            section = section,
                            state = state,
                            onOpenEntity = onOpenEntity,
                            onPlay = onPlay,
                            onOpenSearch = onOpenSearch,
                            onRailSelected = onRailSelected,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HomeDiscoverPlannedRail(
    section: HomeDiscoverRailSection,
    state: HomeUiState,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onOpenSearch: (SearchLaunchRequest) -> Unit,
    onRailSelected: (HomeDiscoverRailAttribution) -> Unit,
) {
    fun trackedOpen(route: AppRoute) {
        onRailSelected(section.attributionFor(route))
        onOpenEntity(route)
    }

    when (val content = section.content) {
        is HomeDiscoverRailSection.Content.ShowsTonight ->
            ShowsTonightRail(
                shows = content.shows,
                onOpenEntity = ::trackedOpen,
                onOpenSearch = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.TONIGHT, state)) },
            )
        is HomeDiscoverRailSection.Content.FollowedComedianShows ->
            FollowedComedianShowsRail(
                shows = content.shows,
                onOpenEntity = ::trackedOpen,
            )
        is HomeDiscoverRailSection.Content.TrendingThisWeek ->
            ShowListRail(
                eyebrow = "Coming Up",
                title = "Best shows this week",
                emptyMessage = "No upcoming shows are listed near you this week.",
                shows = content.shows,
                onOpenEntity = ::trackedOpen,
                onOpenSearch = {
                    onOpenSearch(homeRailSearchRequest(HomeExpandableRail.BEST_THIS_WEEK, state))
                },
            )
        is HomeDiscoverRailSection.Content.TrendingComedians ->
            ComedianRail(
                comedians = content.comedians,
                onOpenEntity = ::trackedOpen,
                onOpenSearch = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.COMEDIANS, state)) },
            )
        is HomeDiscoverRailSection.Content.PopularClubs ->
            ClubRail(
                clubs = content.clubs,
                onOpenEntity = ::trackedOpen,
                onOpenSearch = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.CLUBS, state)) },
            )
        is HomeDiscoverRailSection.Content.PodcastEpisodes ->
            HomePodcastRail(
                episodes = content.episodes,
                podcasts = emptyList(),
                onOpenEntity = ::trackedOpen,
                onPlay = {
                    onRailSelected(section.attributionForPodcastEpisode(it.episodeId))
                    onPlay(it)
                },
                onBrowsePodcasts = { onOpenSearch(homeRailSearchRequest(HomeExpandableRail.PODCASTS, state)) },
            )
        is HomeDiscoverRailSection.Content.NearbyShows ->
            ShowListRail(
                eyebrow = "Near You",
                title = "More shows nearby",
                emptyMessage = "No more shows are listed nearby.",
                shows = content.shows,
                onOpenEntity = ::trackedOpen,
                onOpenSearch = null,
            )
        is HomeDiscoverRailSection.Content.DynamicShows ->
            DynamicShowListRail(
                railKey = section.railKey,
                label = content.label,
                items = content.items,
                onOpenEntity = ::trackedOpen,
            )
    }
}

internal enum class HomeExpandableRail {
    TONIGHT,
    BEST_THIS_WEEK,
    COMEDIANS,
    CLUBS,
    PODCASTS,
}

internal fun homeRailSearchRequest(
    rail: HomeExpandableRail,
    state: HomeUiState,
    today: LocalDate = LocalDate.now(),
): SearchLaunchRequest =
    when (rail) {
        HomeExpandableRail.TONIGHT -> state.showSearch(today, today)
        HomeExpandableRail.BEST_THIS_WEEK -> state.showSearch(today, today.plusDays(7))
        HomeExpandableRail.COMEDIANS -> SearchLaunchRequest(SearchDestination.COMEDIANS)
        HomeExpandableRail.CLUBS ->
            SearchLaunchRequest(
                destination = SearchDestination.CLUBS,
                zip = state.activeZip,
                locationLabel = state.activeLocationLabel,
                distanceMiles = state.distanceMiles,
            )
        HomeExpandableRail.PODCASTS -> SearchLaunchRequest(SearchDestination.PODCASTS)
    }

private fun HomeUiState.showSearch(
    from: LocalDate? = null,
    to: LocalDate? = null,
    filters: Set<String> = emptySet(),
): SearchLaunchRequest =
    SearchLaunchRequest(
        destination = SearchDestination.SHOWS,
        zip = activeZip,
        locationLabel = activeLocationLabel,
        distanceMiles = distanceMiles,
        from = from?.toString(),
        to = to?.toString(),
        filters = filters,
    )

@Composable
private fun ShowsTonightRail(
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
    onOpenSearch: () -> Unit,
) {
    FeedRailCard(
        title = null,
        emptyMessage = "No shows are listed for tonight yet.",
        itemCount = shows.size,
        actionLabel = "See all",
        onAction = onOpenSearch,
    ) {
        FeaturedShowsCarousel(
            headline = "Tonight!",
            items = shows.map { show -> FeaturedShowCarouselItem(show = show) },
            onOpenEntity = onOpenEntity,
        )
    }
}

@Composable
private fun FollowedComedianShowsRail(
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRailCard(
        title = null,
        emptyMessage = "",
        itemCount = shows.size,
    ) {
        FeaturedShowsCarousel(
            headline = "Because you follow them",
            items =
                shows.take(HOME_DISCOVER_RAIL_ITEM_LIMIT).map { show ->
                    FeaturedShowCarouselItem(
                        show = show,
                        preferredHeadlinerId = preferredFavoriteHeadlinerId(show),
                        timestampLabel = formatShowDateTime(show),
                    )
                },
            onOpenEntity = onOpenEntity,
        )
    }
}

@Composable
private fun ShowListRail(
    eyebrow: String?,
    title: String,
    emptyMessage: String,
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
    onOpenSearch: (() -> Unit)?,
) {
    FeedRailCard(
        eyebrow = eyebrow,
        title = title,
        emptyMessage = emptyMessage,
        itemCount = shows.size,
        actionLabel = onOpenSearch?.let { "See all" },
        onAction = onOpenSearch,
    ) {
        shows.forEach { show ->
            ShowListRow(
                show = show,
                onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
            )
        }
    }
}

@Composable
private fun DynamicShowListRail(
    railKey: String,
    label: String,
    items: List<HomeFeedDynamicRailItem>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRailCard(
        eyebrow = if (isTodayStyleDynamicShowRail(railKey)) null else "Picked for you",
        title = label.takeUnless { isTodayStyleDynamicShowRail(railKey) },
        emptyMessage = "",
        itemCount = items.size,
    ) {
        if (isTodayStyleDynamicShowRail(railKey)) {
            FeaturedShowsCarousel(
                headline = label,
                items =
                    items.map { item ->
                        FeaturedShowCarouselItem(
                            show = item.show,
                            preferredHeadlinerId = preferredDynamicRailHeadlinerId(railKey, item),
                            accessibilityReasonLabel = item.reason.label,
                            timestampLabel = formatShowDateTime(item.show),
                        )
                    },
                onOpenEntity = onOpenEntity,
            )
        } else {
            items.forEach { item ->
                ShowListRow(
                    show = item.show,
                    preferredHeadlinerId = preferredDynamicRailHeadlinerId(railKey, item),
                    accessibilityReasonLabel = item.reason.label,
                    onClick = { onOpenEntity(AppRoute.ShowDetail(item.show.id)) },
                )
            }
        }
    }
}

@Composable
private fun ComedianRail(
    comedians: List<ComedianListItem>,
    onOpenEntity: (AppRoute) -> Unit,
    onOpenSearch: () -> Unit,
) {
    FeedRailCard(
        title = "Comedians to watch",
        emptyMessage = "No comedians found.",
        itemCount = comedians.size,
        actionLabel = "See all",
        onAction = onOpenSearch,
    ) {
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(comedians, key = { it.uuid }) { comedian ->
                FeedCard(
                    title = comedian.name,
                    subtitle = "${comedian.showCount} shows",
                    imageUrl = comedian.imageUrl,
                    fallback = RemoteImageFallback.Comedian,
                    width = 156.dp,
                    onClick = { onOpenEntity(AppRoute.ComedianDetail(comedian.id)) },
                )
            }
        }
    }
}

@Composable
private fun ClubRail(
    clubs: List<ClubListItem>,
    onOpenEntity: (AppRoute) -> Unit,
    onOpenSearch: () -> Unit,
) {
    FeedRailCard(
        title = "Popular clubs",
        emptyMessage = "No clubs found.",
        itemCount = clubs.size,
        actionLabel = "See all",
        onAction = onOpenSearch,
    ) {
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(clubs, key = { it.id }) { club ->
                FeedCard(
                    title = club.name,
                    subtitle = club.address,
                    imageUrl = club.imageUrl,
                    fallback = RemoteImageFallback.Club,
                    width = 168.dp,
                    onClick = { onOpenEntity(AppRoute.ClubDetail(club.id)) },
                )
            }
        }
    }
}

@Composable
internal fun FeedRailCard(
    eyebrow: String? = null,
    title: String?,
    emptyMessage: String,
    itemCount: Int,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Box(modifier = Modifier.fillMaxWidth()) {
        Surface(
            color = LaughTrackColors.SurfaceElevated,
            shape = RoundedCornerShape(14.dp),
            modifier =
                Modifier
                    .fillMaxWidth()
                    .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(14.dp)),
        ) {
            Column(
                modifier = Modifier.padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (title != null) {
                    ShelfHeader(eyebrow = eyebrow, title = title)
                }
                if (itemCount == 0) {
                    Text(
                        emptyMessage,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 6.dp),
                    )
                } else {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        content()
                        if (actionLabel != null && onAction != null) {
                            FeedRailAction(label = actionLabel, onClick = onAction)
                        }
                    }
                }
            }
        }
        Box(
            modifier =
                Modifier
                    .align(Alignment.TopStart)
                    .padding(start = 10.dp)
                    .width(52.dp)
                    .height(2.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(LaughTrackColors.AccentStrong.copy(alpha = 0.72f)),
        )
    }
}

@Composable
private fun ShelfHeader(
    eyebrow: String?,
    title: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        if (eyebrow != null) {
            Text(
                eyebrow.uppercase(Locale.US),
                style = MaterialTheme.typography.labelSmall,
                color = LaughTrackColors.AccentStrong,
            )
        }
        Text(
            title,
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

private data class FeaturedShowCarouselItem(
    val show: Show,
    val preferredHeadlinerId: Int? = null,
    val accessibilityReasonLabel: String? = null,
    val timestampLabel: String? = null,
)

@Composable
private fun FeaturedShowsCarousel(
    headline: String,
    items: List<FeaturedShowCarouselItem>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    val listState = rememberLazyListState()
    val selectedIndex by remember(listState, items.size) {
        derivedStateOf { tonightSelectedIndex(listState.firstVisibleItemIndex, items.size) }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Surface(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(432.dp),
            color = LaughTrackColors.Surface,
            shape = RoundedCornerShape(12.dp),
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(
                    text = headline.uppercase(Locale.US),
                    color = LaughTrackColors.AccentStrong,
                    fontWeight = FontWeight.Black,
                    fontSize = if (headline.length > 14) 18.sp else 22.sp,
                    letterSpacing = if (headline.length > 14) 1.8.sp else 2.4.sp,
                    maxLines = 1,
                )

                BoxWithConstraints(
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .weight(1f),
                ) {
                    val pageWidth = maxWidth
                    LazyRow(
                        modifier = Modifier.fillMaxSize(),
                        state = listState,
                        flingBehavior = rememberSnapFlingBehavior(lazyListState = listState),
                    ) {
                        items(items, key = { it.show.id }) { item ->
                            FeaturedShowHeroPage(
                                item = item,
                                modifier =
                                    Modifier
                                        .width(pageWidth)
                                        .fillParentMaxHeight(),
                                onClick = { onOpenEntity(AppRoute.ShowDetail(item.show.id)) },
                            )
                        }
                    }
                }
            }
        }

        TonightPageIndicator(itemCount = items.size, selectedIndex = selectedIndex)
    }
}

internal fun tonightSelectedIndex(
    firstVisibleItemIndex: Int,
    showCount: Int,
): Int = firstVisibleItemIndex.coerceIn(0, (showCount - 1).coerceAtLeast(0))

@Composable
private fun FeaturedShowHeroPage(
    item: FeaturedShowCarouselItem,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val show = item.show
    TonightHeroCard(
        content =
            TonightHeroCardContent(
                timeLabel = item.timestampLabel ?: formatShowTime(show).orEmpty(),
                title = show.name ?: "Show",
                venueLabel = "At ${show.clubName ?: "Unknown club"}",
                artworkUrl = heroArtworkUrl(show, item.preferredHeadlinerId),
                artworkCaption = heroArtworkCaption(show, item.preferredHeadlinerId),
                artworkContentDescription = show.name ?: "Show",
                artworkFallback =
                    if (heroArtworkComedian(show, item.preferredHeadlinerId) != null) {
                        RemoteImageFallback.Comedian
                    } else {
                        RemoteImageFallback.Show
                    },
                priceLabel = formatPrice(show.tickets?.mapNotNull { it.price }),
            ),
        onClick = onClick,
        modifier =
            modifier.then(
                item.accessibilityReasonLabel?.let { reason ->
                    Modifier.semantics {
                        contentDescription = homeDiscoverDynamicShowContentDescription(show, reason)
                    }
                } ?: Modifier,
            ),
    )
}

@Composable
private fun TonightPageIndicator(
    itemCount: Int,
    selectedIndex: Int,
) {
    if (itemCount > 1) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            repeat(itemCount) { index ->
                Box(
                    modifier =
                        Modifier
                            .size(7.dp)
                            .clip(CircleShape)
                            .background(
                                if (index == selectedIndex) {
                                    MaterialTheme.colorScheme.onSurface
                                } else {
                                    MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
                                },
                            ),
                )
            }
        }
    }
}

@Composable
private fun ShowListRow(
    show: Show,
    preferredHeadlinerId: Int? = null,
    accessibilityReasonLabel: String? = null,
    onClick: () -> Unit,
) {
    TicketShowRow(
        dateParts = ticketStubDateParts(isoDateTime = show.date, timezone = show.timezone),
        priceLabel = formatPrice(show.tickets?.mapNotNull { it.price }),
        onClick = onClick,
        modifier =
            if (accessibilityReasonLabel == null) {
                Modifier
            } else {
                Modifier.semantics {
                    contentDescription = homeDiscoverDynamicShowContentDescription(show, accessibilityReasonLabel)
                }
            },
        colors =
            TicketShowRowColors(
                paper = LaughTrackColors.SurfaceElevated,
                border = LaughTrackColors.BorderSubtle,
                divider = LaughTrackColors.ForegroundMuted.copy(alpha = 0.6f),
                stub =
                    TicketStubColors(
                        background = LaughTrackColors.Surface,
                        accent = LaughTrackColors.AccentStrong,
                        primary = MaterialTheme.colorScheme.onSurface,
                        muted = MaterialTheme.colorScheme.onSurfaceVariant,
                    ),
            ),
    ) { bodyModifier ->
        ShowTicketBody(
            show = show,
            preferredHeadlinerId = preferredHeadlinerId,
            modifier = bodyModifier,
        )
    }
}

internal fun homeDiscoverDynamicShowContentDescription(
    show: Show,
    reasonLabel: String,
): String = "${showListTitle(show)}. $reasonLabel"

@Composable
private fun ShowTicketBody(
    show: Show,
    preferredHeadlinerId: Int? = null,
    modifier: Modifier = Modifier,
) {
    val headliner = showHeadliner(show, preferredHeadlinerId)
    val supporting = showSupportingLineup(show, excluding = headliner)
    Box(
        modifier =
            modifier.background(LaughTrackColors.AccentMuted.copy(alpha = 0.035f)),
        contentAlignment = Alignment.CenterStart,
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (headliner != null) {
                ShowHeadlinerBlock(show = show, headliner = headliner, supporting = supporting)
            } else {
                ShowTitleOnlyBlock(show = show)
            }

            val badges = showTicketBadges(show)
            if (badges.isNotEmpty()) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    badges.forEach { badge ->
                        Text(
                            text = badge,
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                            color = LaughTrackColors.AccentStrong,
                            modifier =
                                Modifier
                                    .clip(RoundedCornerShape(999.dp))
                                    .background(LaughTrackColors.AccentMuted.copy(alpha = 0.22f))
                                    .border(
                                        1.dp,
                                        LaughTrackColors.AccentMuted.copy(alpha = 0.45f),
                                        RoundedCornerShape(999.dp),
                                    )
                                    .padding(horizontal = 8.dp, vertical = 2.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ShowHeadlinerBlock(
    show: Show,
    headliner: ComedianLineup,
    supporting: List<ComedianLineup>,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RemoteImage(
                url = headliner.imageUrl,
                fallback = RemoteImageFallback.Comedian,
                contentDescription = headliner.name,
                modifier =
                    Modifier
                        .size(60.dp)
                        .clip(CircleShape)
                        .border(1.5.dp, LaughTrackColors.AccentMuted.copy(alpha = 0.35f), CircleShape),
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Text(
                    headliner.name,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                show.clubName?.takeIf { it.isNotBlank() }?.let { clubName ->
                    Text(
                        clubName,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }

        if (supporting.isNotEmpty()) {
            Text(
                text = "with ${supporting.take(3).joinToString(", ") { it.name }}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun ShowTitleOnlyBlock(show: Show) {
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(
            showListTitle(show),
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        show.clubName?.takeIf { it.isNotBlank() }?.let { clubName ->
            Text(
                clubName,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        roomLabel(show)?.let { room ->
            Text(
                room,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
internal fun FeedRailAction(
    label: String = "See all",
    onClick: () -> Unit,
) {
    Surface(
        color = LaughTrackColors.Surface,
        shape = RoundedCornerShape(999.dp),
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(999.dp))
                .clickable(onClick = onClick)
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.Search, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(label, style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
internal fun FeedCard(
    title: String,
    subtitle: String?,
    imageUrl: String?,
    fallback: RemoteImageFallback,
    width: Dp,
    onClick: () -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .width(width)
                .height(178.dp)
                .clip(RoundedCornerShape(12.dp))
                .clickable(onClick = onClick),
        color = LaughTrackColors.Surface,
        shape = RoundedCornerShape(12.dp),
    ) {
        Column {
            RemoteImage(
                url = imageUrl,
                contentDescription = title,
                modifier = Modifier.fillMaxWidth().height(106.dp),
                fallback = fallback,
            )
            Column(
                Modifier.padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                subtitle?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun HomeLoading(modifier: Modifier = Modifier) {
    Column(
        modifier =
            modifier
                .fillMaxSize()
                .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(text = "Discover", style = MaterialTheme.typography.headlineLarge)
        Text(
            text = "Comedy near you",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        repeat(3) {
            SkeletonLine(Modifier.fillMaxWidth(0.4f))
            SkeletonBox(Modifier.fillMaxWidth().height(140.dp))
        }
    }
}

@Composable
private fun HomeError(
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Surface(
            modifier = Modifier.size(44.dp),
            color = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
            shape = CircleShape,
        ) {
            Text("!", modifier = Modifier.padding(horizontal = 18.dp, vertical = 9.dp))
        }
        Text("Discover could not load.", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Check your connection and try again.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onRetry) { Text("Retry") }
    }
}

@Preview
@Composable
private fun HomeScreenPreview() {
    LaughTrackTheme {
        HomeLoading()
    }
}
