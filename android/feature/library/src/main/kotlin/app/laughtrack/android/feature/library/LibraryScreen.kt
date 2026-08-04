package app.laughtrack.android.feature.library

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.math.BigDecimal
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

private val LibraryMaxWidth = 760.dp

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
            eyebrow = "Plans",
            title = "Next Up",
            subtitle = "The shows you chose are always first.",
        ),
    ),
    FROM_FOLLOWS(
        LibrarySectionPresentation(
            eyebrow = "Following",
            title = "From Your Follows",
            subtitle = "Upcoming shows from comedians you follow.",
        ),
    ),
    SAVED(
        LibrarySectionPresentation(
            eyebrow = "Your collection",
            title = "Saved",
            subtitle = "Comedians, clubs, and podcasts you want to keep close.",
        ),
    ),
    HISTORY(
        LibrarySectionPresentation(
            eyebrow = "Past plans",
            title = "History",
            subtitle = "Past shows you saved.",
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
    val fromFollows: LibraryGroupResolution,
    val saved: LibraryGroupResolution,
    val history: LibraryGroupResolution,
) {
    val isFullyEmpty: Boolean
        get() =
            listOf(nextUp, fromFollows, saved, history)
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

internal sealed interface SavedShowCollectionPresentationState {
    data object Loading : SavedShowCollectionPresentationState

    data class Error(val message: String) : SavedShowCollectionPresentationState

    data object Empty : SavedShowCollectionPresentationState

    data class Content(
        val shows: List<Show>,
        val isRefreshing: Boolean = false,
        val errorMessage: String? = null,
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
            )
        collection.errorMessage != null ->
            SavedShowCollectionPresentationState.Error(collection.errorMessage.orEmpty())
        collection.isLoading || !initialRefreshComplete -> SavedShowCollectionPresentationState.Loading
        else -> SavedShowCollectionPresentationState.Empty
    }

internal fun savedShowNavigationId(show: Show): Int = show.id

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
        fromFollows =
            favoriteResolution(
                hasContent = snapshot.shows.isNotEmpty(),
                snapshot = snapshot,
                initialRefreshComplete = initialRefreshComplete,
            ),
        saved =
            favoriteResolution(
                hasContent =
                    snapshot.comedians.isNotEmpty() ||
                        snapshot.clubs.isNotEmpty() ||
                        snapshot.podcasts.isNotEmpty(),
                snapshot = snapshot,
                initialRefreshComplete = initialRefreshComplete,
            ),
        history =
            savedShowResolution(
                savedShowsSnapshot.past,
                initialRefreshComplete,
            ),
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
        snapshot.errorMessage != null -> LibraryGroupResolution.FAILURE
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
    scopedShowIds: List<Int> = emptyList(),
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
        scopedShowIds = scopedShowIds,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
        onOpenSaved = onOpenSaved,
        onOpenSearch = onOpenSearch,
        onRetrySavedShows = viewModel::refreshSavedShows,
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
    initialRefreshComplete: Boolean = true,
    scopedShowIds: List<Int> = emptyList(),
) {
    LibraryContent(
        signedIn = signedIn,
        snapshot = snapshotOverride,
        savedShowsSnapshot = savedShowsSnapshotOverride,
        message = null,
        initialRefreshComplete = initialRefreshComplete,
        scopedShowIds = scopedShowIds,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
        onOpenSaved = onOpenSaved,
        onOpenSearch = onOpenSearch,
        onRetrySavedShows = {},
        onClearMessage = {},
        onToggleComedian = {},
        onToggleClub = {},
        onTogglePodcast = {},
    )
}

@Composable
private fun LibraryContent(
    signedIn: Boolean,
    snapshot: FavoritesSnapshot,
    savedShowsSnapshot: SavedShowsSnapshot,
    message: String?,
    initialRefreshComplete: Boolean,
    scopedShowIds: List<Int>,
    onOpenProfile: () -> Unit,
    onOpenShow: (Int) -> Unit,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onOpenSearch: (LibrarySearchSeed) -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
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
                    scopedShowIds = scopedShowIds,
                    onOpenShow = onOpenShow,
                    onOpenSaved = onOpenSaved,
                    onOpenSearch = onOpenSearch,
                    onRetrySavedShows = onRetrySavedShows,
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
    scopedShowIds: List<Int>,
    onOpenShow: (Int) -> Unit,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onOpenSearch: (LibrarySearchSeed) -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
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
                )
            LibrarySection.FROM_FOLLOWS ->
                FromFollowsSection(
                    snapshot = snapshot,
                    resolution = contentState.fromFollows,
                    scopedShowIds = scopedShowIds,
                    onOpenShow = onOpenShow,
                )
            LibrarySection.SAVED ->
                SavedEntitiesSection(
                    snapshot = snapshot,
                    resolution = contentState.saved,
                    onOpenSaved = onOpenSaved,
                    onToggleComedian = onToggleComedian,
                    onToggleClub = onToggleClub,
                    onTogglePodcast = onTogglePodcast,
                )
            LibrarySection.HISTORY ->
                SavedShowsSection(
                    section = section,
                    collection = savedShowsSnapshot.past,
                    initialRefreshComplete = initialRefreshComplete,
                    onOpenShow = onOpenShow,
                    onRetry = { onRetrySavedShows(SavedShowPeriod.PAST) },
                )
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
private fun SavedShowsSection(
    section: LibrarySection,
    collection: SavedShowsCollection,
    initialRefreshComplete: Boolean,
    onOpenShow: (Int) -> Unit,
    onRetry: () -> Unit,
) {
    val state = savedShowCollectionState(collection, initialRefreshComplete)
    if (state == SavedShowCollectionPresentationState.Empty) return

    FavoriteSection(section.presentation) {
        when (state) {
            SavedShowCollectionPresentationState.Loading -> LoadingRow()
            is SavedShowCollectionPresentationState.Error -> {
                EmptyText(state.message)
                TextButton(onClick = onRetry) { Text("Retry ${section.presentation.title.lowercase()}") }
            }
            SavedShowCollectionPresentationState.Empty -> Unit
            is SavedShowCollectionPresentationState.Content -> {
                if (state.isRefreshing) LoadingRow()
                state.errorMessage?.let { error ->
                    EmptyText(error)
                    TextButton(onClick = onRetry) { Text("Retry ${section.presentation.title.lowercase()}") }
                }
                state.shows.forEach { show ->
                    SavedShowRow(show = show, onOpenShow = onOpenShow)
                }
            }
        }
    }
}

@Composable
private fun SavedShowRow(
    show: Show,
    onOpenShow: (Int) -> Unit,
) {
    TicketShowRow(
        title = show.name ?: show.clubName ?: "Comedy show",
        subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" - "),
        imageUrl = show.imageUrl,
        dateParts = ticketStubDateParts(show.date, show.timezone),
        priceLabel = savedShowPriceLabel(show.tickets?.mapNotNull { it.price }),
        onClick = { onOpenShow(savedShowNavigationId(show)) },
    )
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
private fun FromFollowsSection(
    snapshot: FavoritesSnapshot,
    resolution: LibraryGroupResolution,
    scopedShowIds: List<Int>,
    onOpenShow: (Int) -> Unit,
) {
    if (resolution == LibraryGroupResolution.EMPTY) return

    var showAll by remember { mutableStateOf(false) }
    val isScoped = scopedShowIds.isNotEmpty() && !showAll
    val shows =
        if (isScoped) {
            val scoped = scopedShowIds.toSet()
            snapshot.shows.filter { it.id in scoped }
        } else {
            snapshot.shows.take(4)
        }
    val presentation =
        if (isScoped) {
            LibrarySection.FROM_FOLLOWS.presentation.copy(title = "From Your Notification")
        } else {
            LibrarySection.FROM_FOLLOWS.presentation
        }

    FavoriteSection(presentation) {
        when (resolution) {
            LibraryGroupResolution.LOADING -> LoadingRow()
            LibraryGroupResolution.FAILURE ->
                EmptyText(
                    snapshot.errorMessage ?: "Couldn’t load shows from your follows.",
                )
            LibraryGroupResolution.EMPTY -> Unit
            LibraryGroupResolution.CONTENT -> {
                if (isScoped) {
                    TextButton(onClick = { showAll = true }) { Text("Show all follows") }
                }
                if (shows.isEmpty()) {
                    EmptyText("Those shows aren’t in your upcoming follows right now.")
                } else {
                    shows.forEach { show ->
                        ShowRow(show = show, onOpenShow = onOpenShow)
                    }
                }
            }
        }
    }
}

@Composable
private fun SavedEntitiesSection(
    snapshot: FavoritesSnapshot,
    resolution: LibraryGroupResolution,
    onOpenSaved: (LibrarySavedDestination) -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    if (resolution == LibraryGroupResolution.EMPTY) return

    FavoriteSection(LibrarySection.SAVED.presentation) {
        when (resolution) {
            LibraryGroupResolution.LOADING -> LoadingRow()
            LibraryGroupResolution.FAILURE -> EmptyText(snapshot.errorMessage ?: "Couldn’t load your saved collection.")
            LibraryGroupResolution.EMPTY -> Unit
            LibraryGroupResolution.CONTENT -> {
                if (snapshot.comedians.isNotEmpty()) {
                    SavedGroupTitle("Comedians")
                    snapshot.comedians.forEach { comedian ->
                        FavoriteRow(
                            title = comedian.name,
                            subtitle = "${comedian.showCount} upcoming shows",
                            onOpen = { onOpenSaved(savedComedianDestination(comedian)) },
                            onRemove = { onToggleComedian(comedian.uuid) },
                        )
                    }
                }
                if (snapshot.clubs.isNotEmpty()) {
                    SavedGroupTitle("Clubs")
                    snapshot.clubs.forEach { club ->
                        ClubRow(
                            club = club,
                            onOpen = { onOpenSaved(savedClubDestination(club)) },
                            onRemove = { onToggleClub(club.id) },
                        )
                    }
                }
                if (snapshot.podcasts.isNotEmpty()) {
                    SavedGroupTitle("Podcasts")
                    snapshot.podcasts.forEach { podcast ->
                        PodcastRow(
                            podcast = podcast,
                            onOpen = { onOpenSaved(savedPodcastDestination(podcast)) },
                            onRemove = { onTogglePodcast(podcast.id) },
                        )
                    }
                }
            }
        }
    }
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
            Text(
                presentation.eyebrow.uppercase(Locale.US),
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = LaughTrackColors.AccentStrong,
            )
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
private fun FavoriteRow(
    title: String,
    subtitle: String,
    onOpen: () -> Unit,
    onRemove: (() -> Unit)?,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier =
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .clickable(onClick = onOpen)
                    .padding(vertical = 8.dp, horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (onRemove != null) {
            TextButton(onClick = onRemove) { Text("Remove") }
        }
    }
}

@Composable
private fun ShowRow(
    show: Show,
    onOpenShow: (Int) -> Unit,
) {
    FavoriteRow(
        title = show.name ?: show.clubName ?: "Comedy show",
        subtitle = favoriteShowSubtitle(show),
        onOpen = { onOpenShow(show.id) },
        onRemove = null,
    )
}

internal fun favoriteShowSubtitle(
    show: Show,
    locale: Locale = Locale.getDefault(),
): String {
    val formattedDate = formatFavoriteShowDate(show, locale)
    return listOfNotNull(show.clubName, show.clubCity, formattedDate).joinToString(" - ")
}

private fun formatFavoriteShowDate(
    show: Show,
    locale: Locale,
): String? {
    val raw = show.date.trim()
    if (raw.isEmpty()) return null

    val venueZone = show.timezone?.let { runCatching { ZoneId.of(it) }.getOrNull() }
    val dateTime =
        runCatching {
            val parsed = OffsetDateTime.parse(raw)
            venueZone?.let(parsed::atZoneSameInstant) ?: parsed.toZonedDateTime()
        }
            .recoverCatching {
                val parsed = ZonedDateTime.parse(raw)
                venueZone?.let(parsed::withZoneSameInstant) ?: parsed
            }
            .recoverCatching {
                LocalDateTime.parse(raw).atZone(venueZone ?: ZoneId.systemDefault())
            }
            .getOrNull()
            ?: return null

    val dateFormatter = DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(locale)
    val timeFormatter = DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale)
    return "${dateTime.format(dateFormatter)} · ${dateTime.format(timeFormatter)}"
}

@Composable
private fun ClubRow(
    club: FavoriteClubItem,
    onOpen: () -> Unit,
    onRemove: () -> Unit,
) {
    FavoriteRow(
        title = club.name,
        subtitle = "Saved club",
        onOpen = onOpen,
        onRemove = onRemove,
    )
}

@Composable
private fun PodcastRow(
    podcast: FavoritePodcastItem,
    onOpen: () -> Unit,
    onRemove: () -> Unit,
) {
    FavoriteRow(
        title = podcast.title,
        subtitle = podcast.authorName ?: "${podcast.episodeCount} episodes",
        onOpen = onOpen,
        onRemove = onRemove,
    )
}

@Composable
private fun SavedGroupTitle(title: String) {
    Text(
        text = title.uppercase(Locale.US),
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
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
