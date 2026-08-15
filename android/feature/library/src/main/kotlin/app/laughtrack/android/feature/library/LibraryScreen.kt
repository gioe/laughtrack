package app.laughtrack.android.feature.library

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.savedshows.SavedShowPeriod
import app.laughtrack.android.core.data.savedshows.SavedShowsCollection
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.components.EntityArtwork
import app.laughtrack.android.core.ui.components.SearchEntityKind
import app.laughtrack.android.core.ui.components.SearchEntityRow
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.TicketShowRowDefaults
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.math.BigDecimal
import java.util.Locale

private val LibraryMaxWidth = 760.dp
internal const val LIBRARY_RAIL_PAGE_SIZE = 5

internal data class LibrarySectionPresentation(
    val eyebrow: String,
    val title: String,
    val subtitle: String,
)

internal enum class LibrarySection(
    val presentation: LibrarySectionPresentation,
) {
    NEXT_UP(
        LibrarySectionPresentation(
            eyebrow = "",
            title = "Shows",
            subtitle = "",
        ),
    ),
    COMEDIANS(
        LibrarySectionPresentation(
            eyebrow = "",
            title = "Comedians",
            subtitle = "",
        ),
    ),
    CLUBS(
        LibrarySectionPresentation(
            eyebrow = "",
            title = "Clubs",
            subtitle = "",
        ),
    ),
    PODCASTS(
        LibrarySectionPresentation(
            eyebrow = "",
            title = "Podcasts",
            subtitle = "",
        ),
    ),
}

internal enum class LibraryGroupResolution {
    LOADING,
    CONTENT,
    EMPTY,
    FAILURE,
}

internal data class LibraryContentState(
    val nextUp: LibraryGroupResolution,
    val comedians: LibraryGroupResolution,
    val clubs: LibraryGroupResolution,
    val podcasts: LibraryGroupResolution,
    val favoritesErrorMessage: String? = null,
) {
    val isFullyEmpty: Boolean
        get() =
            favoritesErrorMessage == null &&
                listOf(nextUp, comedians, clubs, podcasts)
                    .all { it == LibraryGroupResolution.EMPTY }
}

/** One-shot Search requests emitted by the Library empty state. */
enum class LibrarySearchSeed(
    val label: String,
    val nearMe: Boolean = false,
) {
    SHOWS("Shows near me", nearMe = true),
    COMEDIANS("Follow comedians"),
    CLUBS("Save clubs"),
    PODCASTS("Save podcasts"),
}

/** Detail destinations emitted by rows in the unified Saved collection. */
sealed interface LibrarySavedDestination {
    data class Comedian(val id: Int) : LibrarySavedDestination

    data class Club(val id: Int) : LibrarySavedDestination

    data class Podcast(val id: Int) : LibrarySavedDestination
}

internal fun savedComedianDestination(comedian: ComedianSearchItem): LibrarySavedDestination =
    LibrarySavedDestination.Comedian(comedian.id)

internal fun savedClubDestination(club: FavoriteClubItem): LibrarySavedDestination =
    LibrarySavedDestination.Club(club.id)

internal fun savedPodcastDestination(podcast: FavoritePodcastItem): LibrarySavedDestination =
    LibrarySavedDestination.Podcast(podcast.id)

internal fun libraryEntityKind(section: LibrarySection): SearchEntityKind? =
    when (section) {
        LibrarySection.NEXT_UP -> null
        LibrarySection.COMEDIANS -> SearchEntityKind.COMEDIAN
        LibrarySection.CLUBS -> SearchEntityKind.CLUB
        LibrarySection.PODCASTS -> SearchEntityKind.PODCAST
    }

internal sealed interface SavedShowCollectionPresentationState {
    data object Loading : SavedShowCollectionPresentationState

    data class Error(val message: String) : SavedShowCollectionPresentationState

    data object Empty : SavedShowCollectionPresentationState

    data class Content(
        val shows: List<Show>,
        val isRefreshing: Boolean = false,
        val errorMessage: String? = null,
        val canLoadMore: Boolean = false,
    ) : SavedShowCollectionPresentationState
}

internal fun savedShowCollectionState(
    collection: SavedShowsCollection,
    initialRefreshComplete: Boolean = true,
): SavedShowCollectionPresentationState =
    when {
        collection.shows.isNotEmpty() ->
            SavedShowCollectionPresentationState.Content(
                shows = collection.shows,
                isRefreshing = collection.isLoading,
                errorMessage = collection.errorMessage,
                canLoadMore = collection.page > 0 && collection.page < collection.totalPages,
            )
        collection.errorMessage != null ->
            SavedShowCollectionPresentationState.Error(collection.errorMessage.orEmpty())
        collection.isLoading || !initialRefreshComplete -> SavedShowCollectionPresentationState.Loading
        else -> SavedShowCollectionPresentationState.Empty
    }

internal fun savedShowNavigationId(show: Show): Int = show.id

internal fun savedShowsForPage(
    shows: List<Show>,
    page: Int,
): List<Show> = libraryItemsForPage(shows, page)

internal fun <T> libraryItemsForPage(
    items: List<T>,
    page: Int,
): List<T> =
    items
        .drop(page.coerceAtLeast(0) * LIBRARY_RAIL_PAGE_SIZE)
        .take(LIBRARY_RAIL_PAGE_SIZE)

internal fun libraryPageCount(itemCount: Int): Int =
    maxOf(1, (itemCount + LIBRARY_RAIL_PAGE_SIZE - 1) / LIBRARY_RAIL_PAGE_SIZE)

internal fun libraryPageAfterCollectionUpdate(
    displayedPage: Int,
    loadedItemCount: Int,
): Int = if (displayedPage * LIBRARY_RAIL_PAGE_SIZE < loadedItemCount) displayedPage else 0

internal fun libraryContentState(
    snapshot: FavoritesSnapshot,
    savedShowsSnapshot: SavedShowsSnapshot,
    initialRefreshComplete: Boolean,
): LibraryContentState =
    LibraryContentState(
        nextUp =
            savedShowResolution(
                savedShowsSnapshot.upcoming,
                initialRefreshComplete,
            ),
        comedians =
            favoriteResolution(
                hasContent = snapshot.comedians.isNotEmpty(),
                snapshot = snapshot,
                initialRefreshComplete = initialRefreshComplete,
            ),
        clubs =
            favoriteResolution(
                hasContent = snapshot.clubs.isNotEmpty(),
                snapshot = snapshot,
                initialRefreshComplete = initialRefreshComplete,
            ),
        podcasts =
            favoriteResolution(
                hasContent = snapshot.podcasts.isNotEmpty(),
                snapshot = snapshot,
                initialRefreshComplete = initialRefreshComplete,
            ),
        favoritesErrorMessage = snapshot.errorMessage,
    )

private fun savedShowResolution(
    collection: SavedShowsCollection,
    initialRefreshComplete: Boolean,
): LibraryGroupResolution =
    when (savedShowCollectionState(collection, initialRefreshComplete)) {
        SavedShowCollectionPresentationState.Loading -> LibraryGroupResolution.LOADING
        is SavedShowCollectionPresentationState.Error -> LibraryGroupResolution.FAILURE
        SavedShowCollectionPresentationState.Empty -> LibraryGroupResolution.EMPTY
        is SavedShowCollectionPresentationState.Content -> LibraryGroupResolution.CONTENT
    }

private fun favoriteResolution(
    hasContent: Boolean,
    snapshot: FavoritesSnapshot,
    initialRefreshComplete: Boolean,
): LibraryGroupResolution =
    when {
        hasContent -> LibraryGroupResolution.CONTENT
        snapshot.isLoading || !initialRefreshComplete -> LibraryGroupResolution.LOADING
        else -> LibraryGroupResolution.EMPTY
    }

@Composable
fun LibraryScreen(
    signedIn: Boolean,
    onOpenProfile: () -> Unit,
    onOpenShow: (Int) -> Unit = {},
    onOpenSaved: (LibrarySavedDestination) -> Unit = {},
    onOpenSearch: (LibrarySearchSeed) -> Unit = {},
    viewModel: LibraryViewModel = hiltViewModel(),
) {
    val snapshot by viewModel.snapshot.collectAsState()
    val savedShowsSnapshot by viewModel.savedShowsSnapshot.collectAsState()
    val initialRefreshComplete by viewModel.initialRefreshComplete.collectAsState()
    val message by viewModel.message.collectAsState()

    LaunchedEffect(signedIn) {
        viewModel.refresh(signedIn)
    }

    LibraryContent(
        signedIn = signedIn,
        snapshot = snapshot,
        savedShowsSnapshot = savedShowsSnapshot,
        message = message,
        initialRefreshComplete = initialRefreshComplete,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
        onOpenSaved = onOpenSaved,
        onOpenSearch = onOpenSearch,
        onRetryFavorites = viewModel::refreshFavorites,
        onRetrySavedShows = viewModel::refreshSavedShows,
        onLoadMoreSavedShows = viewModel::loadNextSavedShowsPage,
        onClearMessage = viewModel::clearMessage,
        onToggleComedian = viewModel::toggleComedian,
        onToggleClub = viewModel::toggleClub,
        onTogglePodcast = viewModel::togglePodcast,
    )
}

/** Render the real Library UI from deterministic state without creating a Hilt ViewModel. */
@Composable
fun LibraryScreen(
    signedIn: Boolean,
    onOpenProfile: () -> Unit,
    snapshotOverride: FavoritesSnapshot,
    savedShowsSnapshotOverride: SavedShowsSnapshot = SavedShowsSnapshot(),
    onOpenShow: (Int) -> Unit = {},
    onOpenSaved: (LibrarySavedDestination) -> Unit = {},
    onOpenSearch: (LibrarySearchSeed) -> Unit = {},
    onRetryFavorites: () -> Unit = {},
    onRetrySavedShows: (SavedShowPeriod) -> Unit = {},
    onLoadMoreSavedShows: (SavedShowPeriod) -> Unit = {},
    onToggleComedian: (String) -> Unit = {},
    onToggleClub: (Int) -> Unit = {},
    onTogglePodcast: (Int) -> Unit = {},
    initialRefreshComplete: Boolean = true,
) {
    LibraryContent(
        signedIn = signedIn,
        snapshot = snapshotOverride,
        savedShowsSnapshot = savedShowsSnapshotOverride,
        message = null,
        initialRefreshComplete = initialRefreshComplete,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
        onOpenSaved = onOpenSaved,
        onOpenSearch = onOpenSearch,
        onRetryFavorites = onRetryFavorites,
        onRetrySavedShows = onRetrySavedShows,
        onLoadMoreSavedShows = onLoadMoreSavedShows,
        onClearMessage = {},
        onToggleComedian = onToggleComedian,
        onToggleClub = onToggleClub,
        onTogglePodcast = onTogglePodcast,
    )
}

@Composable
private fun LibraryContent(
    signedIn: Boolean,
    snapshot: FavoritesSnapshot,
    savedShowsSnapshot: SavedShowsSnapshot,
    message: String?,
    initialRefreshComplete: Boolean,
    onOpenProfile: () -> Unit,
    onOpenShow: (Int) -> Unit,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onOpenSearch: (LibrarySearchSeed) -> Unit,
    onRetryFavorites: () -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
    onLoadMoreSavedShows: (SavedShowPeriod) -> Unit,
    onClearMessage: () -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier =
                Modifier
                    .align(Alignment.TopCenter)
                    .widthIn(max = LibraryMaxWidth)
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(
                "Library",
                style = MaterialTheme.typography.headlineLarge,
                color = LaughTrackColors.Foreground,
            )

            if (message != null) {
                AssistChip(
                    onClick = onClearMessage,
                    label = { Text(message) },
                )
            }

            if (signedIn) {
                SignedInLibrary(
                    snapshot = snapshot,
                    savedShowsSnapshot = savedShowsSnapshot,
                    initialRefreshComplete = initialRefreshComplete,
                    onOpenShow = onOpenShow,
                    onOpenSaved = onOpenSaved,
                    onOpenSearch = onOpenSearch,
                    onRetryFavorites = onRetryFavorites,
                    onRetrySavedShows = onRetrySavedShows,
                    onLoadMoreSavedShows = onLoadMoreSavedShows,
                    onToggleComedian = onToggleComedian,
                    onToggleClub = onToggleClub,
                    onTogglePodcast = onTogglePodcast,
                )
            } else {
                LibraryEmptyState(
                    requiresSignIn = true,
                    onOpenSearch = onOpenSearch,
                    onOpenProfile = onOpenProfile,
                )
            }
        }
    }
}

@Composable
private fun SignedInLibrary(
    snapshot: FavoritesSnapshot,
    savedShowsSnapshot: SavedShowsSnapshot,
    initialRefreshComplete: Boolean,
    onOpenShow: (Int) -> Unit,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onOpenSearch: (LibrarySearchSeed) -> Unit,
    onRetryFavorites: () -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
    onLoadMoreSavedShows: (SavedShowPeriod) -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    val contentState = libraryContentState(snapshot, savedShowsSnapshot, initialRefreshComplete)

    LibrarySection.entries.forEach { section ->
        when (section) {
            LibrarySection.NEXT_UP ->
                SavedShowsSection(
                    section = section,
                    collection = savedShowsSnapshot.upcoming,
                    initialRefreshComplete = initialRefreshComplete,
                    onOpenShow = onOpenShow,
                    onRetry = { onRetrySavedShows(SavedShowPeriod.UPCOMING) },
                    onLoadMore = { onLoadMoreSavedShows(SavedShowPeriod.UPCOMING) },
                )
            LibrarySection.COMEDIANS,
            LibrarySection.CLUBS,
            LibrarySection.PODCASTS,
            -> {
                if (section == LibrarySection.COMEDIANS && contentState.favoritesErrorMessage != null) {
                    FavoritesSyncFailure(
                        message = contentState.favoritesErrorMessage,
                        onRetry = onRetryFavorites,
                    )
                }
                SavedEntityRail(
                    section = section,
                    snapshot = snapshot,
                    resolution =
                        when (section) {
                            LibrarySection.COMEDIANS -> contentState.comedians
                            LibrarySection.CLUBS -> contentState.clubs
                            LibrarySection.PODCASTS -> contentState.podcasts
                            LibrarySection.NEXT_UP -> error("Saved shows use their own rail")
                        },
                    onOpenSaved = onOpenSaved,
                    onToggleComedian = onToggleComedian,
                    onToggleClub = onToggleClub,
                    onTogglePodcast = onTogglePodcast,
                )
            }
        }
    }

    if (contentState.isFullyEmpty) {
        LibraryEmptyState(
            requiresSignIn = false,
            onOpenSearch = onOpenSearch,
            onOpenProfile = null,
        )
    }
}

@Composable
private fun FavoritesSyncFailure(
    message: String,
    onRetry: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors =
            CardDefaults.cardColors(
                containerColor = LaughTrackColors.SurfaceMuted,
                contentColor = LaughTrackColors.Foreground,
            ),
        border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            EmptyText(message)
            TextButton(onClick = onRetry) { Text("Retry favorites") }
        }
    }
}

@Composable
private fun SavedShowsSection(
    section: LibrarySection,
    collection: SavedShowsCollection,
    initialRefreshComplete: Boolean,
    onOpenShow: (Int) -> Unit,
    onRetry: () -> Unit,
    onLoadMore: () -> Unit,
) {
    val state = savedShowCollectionState(collection, initialRefreshComplete)
    if (state == SavedShowCollectionPresentationState.Empty) return

    var displayedPage by remember { mutableIntStateOf(0) }
    var requestedPage by remember { mutableIntStateOf(0) }

    LaunchedEffect(collection.total, collection.shows.firstOrNull()?.id) {
        displayedPage = 0
        requestedPage = 0
    }

    LaunchedEffect(collection.page, collection.shows.size) {
        val nextDisplayedPage = libraryPageAfterCollectionUpdate(displayedPage, collection.shows.size)
        if (nextDisplayedPage != displayedPage) {
            displayedPage = nextDisplayedPage
            requestedPage = nextDisplayedPage
        }
    }

    LaunchedEffect(collection.shows.size, requestedPage) {
        if (collection.shows.size > requestedPage * LIBRARY_RAIL_PAGE_SIZE) {
            displayedPage = requestedPage
        }
    }

    FavoriteSection(section.presentation) {
        when (state) {
            SavedShowCollectionPresentationState.Loading -> LoadingRow()
            is SavedShowCollectionPresentationState.Error -> {
                EmptyText(state.message)
                TextButton(onClick = onRetry) { Text("Retry ${section.presentation.title.lowercase()}") }
            }
            SavedShowCollectionPresentationState.Empty -> Unit
            is SavedShowCollectionPresentationState.Content -> {
                val pageCount = collection.totalPages.coerceAtLeast(1)
                val currentPage = displayedPage.coerceIn(0, pageCount - 1)

                savedShowsForPage(state.shows, currentPage).forEach { show ->
                    SavedShowRow(show = show, onOpenShow = onOpenShow)
                }
                if (pageCount > 1) {
                    LibraryPager(
                        currentPage = currentPage,
                        pageCount = pageCount,
                        enabled = !state.isRefreshing,
                        onPrevious = {
                            requestedPage = (currentPage - 1).coerceAtLeast(0)
                            displayedPage = requestedPage
                        },
                        onNext = {
                            val targetPage = (currentPage + 1).coerceAtMost(pageCount - 1)
                            requestedPage = targetPage
                            if (state.shows.size > targetPage * LIBRARY_RAIL_PAGE_SIZE) {
                                displayedPage = targetPage
                            } else {
                                onLoadMore()
                            }
                        },
                    )
                }
                if (state.isRefreshing) {
                    LoadingRow()
                } else if (state.errorMessage != null) {
                    EmptyText(state.errorMessage)
                    TextButton(onClick = if (state.canLoadMore) onLoadMore else onRetry) {
                        Text(
                            if (state.canLoadMore) {
                                "Retry loading more"
                            } else {
                                "Retry ${section.presentation.title.lowercase()}"
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LibraryPager(
    currentPage: Int,
    pageCount: Int,
    enabled: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TextButton(
            onClick = onPrevious,
            enabled = enabled && currentPage > 0,
        ) {
            Text("Previous")
        }
        Text(
            text = "Page ${currentPage + 1} of $pageCount",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        TextButton(
            onClick = onNext,
            enabled = enabled && currentPage + 1 < pageCount,
        ) {
            Text("Next")
        }
    }
}

@Composable
private fun SavedShowRow(
    show: Show,
    onOpenShow: (Int) -> Unit,
) {
    val title = show.name ?: show.clubName ?: "Comedy show"
    val subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" - ")
    TicketShowRow(
        dateParts = ticketStubDateParts(show.date, show.timezone),
        priceLabel = savedShowPriceLabel(show.tickets?.mapNotNull { it.price }),
        onClick = { onOpenShow(savedShowNavigationId(show)) },
        minHeight = TicketShowRowDefaults.CompactMinHeight,
    ) { bodyModifier ->
        Row(
            modifier = bodyModifier.padding(10.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            EntityArtwork(
                artworkUrl = show.imageUrl,
                kind = SearchEntityKind.SHOW,
                artworkSize = 56.dp,
                contentDescription = title,
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleSmall,
                    color = LaughTrackColors.TicketInk,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                subtitle.takeIf(String::isNotBlank)?.let { value ->
                    Text(
                        value,
                        style = MaterialTheme.typography.bodySmall,
                        color = LaughTrackColors.TicketInkMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

internal fun savedShowPriceLabel(prices: List<BigDecimal>?): String? {
    val minimum = prices?.minOrNull() ?: return null
    return if (minimum.stripTrailingZeros().scale() <= 0) {
        "\$${minimum.toBigInteger()}"
    } else {
        "\$$minimum"
    }
}

@Composable
private fun SavedEntityRail(
    section: LibrarySection,
    snapshot: FavoritesSnapshot,
    resolution: LibraryGroupResolution,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    if (resolution == LibraryGroupResolution.EMPTY) return

    val itemCount = section.savedEntityCount(snapshot)
    val pageCount = libraryPageCount(itemCount)
    var displayedPage by remember(section) { mutableIntStateOf(0) }
    val currentPage = displayedPage.coerceIn(0, pageCount - 1)

    LaunchedEffect(itemCount) {
        displayedPage = displayedPage.coerceIn(0, pageCount - 1)
    }

    FavoriteSection(section.presentation) {
        when (resolution) {
            LibraryGroupResolution.LOADING -> LoadingRow()
            LibraryGroupResolution.FAILURE -> {
                EmptyText(snapshot.errorMessage ?: "Couldn’t load saved ${section.presentation.title.lowercase()}.")
            }
            LibraryGroupResolution.EMPTY -> Unit
            LibraryGroupResolution.CONTENT -> {
                when (section) {
                    LibrarySection.COMEDIANS -> {
                        libraryItemsForPage(snapshot.comedians, currentPage).forEach { comedian ->
                            SearchEntityRow(
                                title = comedian.name,
                                subtitle = null,
                                artworkUrl = comedian.imageUrl,
                                kind = requireNotNull(libraryEntityKind(section)),
                                onOpen = { onOpenSaved(savedComedianDestination(comedian)) },
                            ) {
                                TextButton(
                                    onClick = { onToggleComedian(comedian.uuid) },
                                    modifier =
                                        Modifier.semantics {
                                            contentDescription = "Remove ${comedian.name}"
                                        },
                                ) { Text("Remove") }
                            }
                        }
                    }
                    LibrarySection.CLUBS -> {
                        libraryItemsForPage(snapshot.clubs, currentPage).forEach { club ->
                            SearchEntityRow(
                                title = club.name,
                                subtitle = "Saved club",
                                artworkUrl = club.imageUrl,
                                kind = requireNotNull(libraryEntityKind(section)),
                                onOpen = { onOpenSaved(savedClubDestination(club)) },
                            ) {
                                TextButton(
                                    onClick = { onToggleClub(club.id) },
                                    modifier =
                                        Modifier.semantics {
                                            contentDescription = "Remove ${club.name}"
                                        },
                                ) { Text("Remove") }
                            }
                        }
                    }
                    LibrarySection.PODCASTS -> {
                        libraryItemsForPage(snapshot.podcasts, currentPage).forEach { podcast ->
                            SearchEntityRow(
                                title = podcast.title,
                                subtitle = podcast.authorName,
                                artworkUrl = podcast.imageUrl,
                                kind = requireNotNull(libraryEntityKind(section)),
                                onOpen = { onOpenSaved(savedPodcastDestination(podcast)) },
                            ) {
                                TextButton(
                                    onClick = { onTogglePodcast(podcast.id) },
                                    modifier =
                                        Modifier.semantics {
                                            contentDescription = "Remove ${podcast.title}"
                                        },
                                ) { Text("Remove") }
                            }
                        }
                    }
                    LibrarySection.NEXT_UP -> Unit
                }
                if (pageCount > 1) {
                    LibraryPager(
                        currentPage = currentPage,
                        pageCount = pageCount,
                        enabled = true,
                        onPrevious = { displayedPage = (currentPage - 1).coerceAtLeast(0) },
                        onNext = { displayedPage = (currentPage + 1).coerceAtMost(pageCount - 1) },
                    )
                }
            }
        }
    }
}

private fun LibrarySection.savedEntityCount(snapshot: FavoritesSnapshot): Int =
    when (this) {
        LibrarySection.COMEDIANS -> snapshot.comedians.size
        LibrarySection.CLUBS -> snapshot.clubs.size
        LibrarySection.PODCASTS -> snapshot.podcasts.size
        LibrarySection.NEXT_UP -> 0
    }

@Composable
private fun LibraryEmptyState(
    requiresSignIn: Boolean,
    onOpenSearch: (LibrarySearchSeed) -> Unit,
    onOpenProfile: (() -> Unit)?,
) {
    FavoriteSection(
        LibrarySectionPresentation(
            eyebrow = "Make it yours",
            title = if (requiresSignIn) "Sign in to build your Library" else "Start your Library",
            subtitle = "",
        ),
    ) {
        EmptyText(
            if (requiresSignIn) {
                "Explore now, then sign in from Profile to keep plans and follows with your account."
            } else {
                "Save a show or follow a comedian, club, or podcast. Your plans and favorites will collect here."
            },
        )
        LibrarySearchSeed.entries.chunked(2).forEach { seeds ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                seeds.forEach { seed ->
                    OutlinedButton(
                        onClick = { onOpenSearch(seed) },
                        modifier = Modifier.weight(1f),
                    ) {
                        Text(seed.label, maxLines = 2)
                    }
                }
                if (seeds.size == 1) Spacer(Modifier.weight(1f))
            }
        }
        if (onOpenProfile != null) {
            Button(onClick = onOpenProfile, modifier = Modifier.fillMaxWidth()) {
                Text("Open Profile to sign in")
            }
        }
    }
}

@Composable
private fun FavoriteSection(
    presentation: LibrarySectionPresentation,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            if (presentation.eyebrow.isNotBlank()) {
                Text(
                    presentation.eyebrow.uppercase(Locale.US),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = LaughTrackColors.AccentStrong,
                )
            }
            Text(
                presentation.title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = LaughTrackColors.Foreground,
            )
            if (presentation.subtitle.isNotBlank()) {
                Text(
                    presentation.subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors =
                CardDefaults.cardColors(
                    containerColor = LaughTrackColors.SurfaceMuted,
                    contentColor = LaughTrackColors.Foreground,
                ),
            border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                content = content,
            )
        }
    }
}

@Composable
private fun LoadingRow() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator()
    }
}

@Composable
private fun EmptyText(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}
