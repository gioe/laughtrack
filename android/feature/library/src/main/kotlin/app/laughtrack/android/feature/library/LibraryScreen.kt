package app.laughtrack.android.feature.library

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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

internal data class LibrarySectionPresentation(
    val eyebrow: String,
    val title: String,
    val subtitle: String,
)

internal enum class SavedShowLibrarySection(
    val period: SavedShowPeriod,
    val presentation: LibrarySectionPresentation,
    val emptyMessage: String,
) {
    UPCOMING(
        period = SavedShowPeriod.UPCOMING,
        presentation =
            LibrarySectionPresentation(
                eyebrow = "Saved shows",
                title = "Upcoming saved shows",
                subtitle = "Shows you want to catch next.",
            ),
        emptyMessage = "Save an upcoming show and it will appear here.",
    ),
    PAST(
        period = SavedShowPeriod.PAST,
        presentation =
            LibrarySectionPresentation(
                eyebrow = "Saved history",
                title = "Past saved shows",
                subtitle = "A record of shows you saved.",
            ),
        emptyMessage = "Past saved shows will collect here.",
    ),
}

internal sealed interface SavedShowCollectionPresentationState {
    data object Loading : SavedShowCollectionPresentationState

    data class Error(val message: String) : SavedShowCollectionPresentationState

    data object Empty : SavedShowCollectionPresentationState

    data class Content(val shows: List<Show>) : SavedShowCollectionPresentationState
}

internal fun savedShowCollectionState(collection: SavedShowsCollection): SavedShowCollectionPresentationState =
    when {
        collection.isLoading -> SavedShowCollectionPresentationState.Loading
        collection.errorMessage != null ->
            SavedShowCollectionPresentationState.Error(collection.errorMessage.orEmpty())
        collection.shows.isEmpty() -> SavedShowCollectionPresentationState.Empty
        else -> SavedShowCollectionPresentationState.Content(collection.shows)
    }

internal fun savedShowNavigationId(show: Show): Int = show.id

internal enum class AuthenticatedLibrarySection(
    val presentation: LibrarySectionPresentation,
) {
    TOURING(
        LibrarySectionPresentation(
            eyebrow = "Favorites",
            title = "Your favorites are touring",
            subtitle = "Upcoming shows from comedians you follow.",
        ),
    ),
    COMEDIANS(
        LibrarySectionPresentation(
            eyebrow = "Comedians",
            title = "Saved comedians",
            subtitle = "We'll keep their nearby dates in one place.",
        ),
    ),
    CLUBS(
        LibrarySectionPresentation(
            eyebrow = "Clubs",
            title = "Saved clubs",
            subtitle = "Keep favorite venue calendars close.",
        ),
    ),
    PODCASTS(
        LibrarySectionPresentation(
            eyebrow = "Podcasts",
            title = "Saved podcasts",
            subtitle = "Find new episodes faster.",
        ),
    ),
}

@Composable
fun LibraryScreen(
    signedIn: Boolean,
    onOpenProfile: () -> Unit,
    onOpenShow: (Int) -> Unit = {},
    scopedShowIds: List<Int> = emptyList(),
    viewModel: LibraryViewModel = hiltViewModel(),
) {
    val snapshot by viewModel.snapshot.collectAsState()
    val savedShowsSnapshot by viewModel.savedShowsSnapshot.collectAsState()
    val message by viewModel.message.collectAsState()

    LaunchedEffect(signedIn) {
        viewModel.refresh(signedIn)
    }

    LibraryContent(
        signedIn = signedIn,
        snapshot = snapshot,
        savedShowsSnapshot = savedShowsSnapshot,
        message = message,
        scopedShowIds = scopedShowIds,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
        onRetrySavedShows = viewModel::refreshSavedShows,
        onClearMessage = viewModel::clearMessage,
        onToggleComedian = viewModel::toggleComedian,
        onToggleClub = viewModel::toggleClub,
        onTogglePodcast = viewModel::togglePodcast,
    )
}

/** Render the real library UI from deterministic state without creating a Hilt ViewModel. */
@Composable
fun LibraryScreen(
    signedIn: Boolean,
    onOpenProfile: () -> Unit,
    snapshotOverride: FavoritesSnapshot,
    savedShowsSnapshotOverride: SavedShowsSnapshot = SavedShowsSnapshot(),
    onOpenShow: (Int) -> Unit = {},
    scopedShowIds: List<Int> = emptyList(),
) {
    LibraryContent(
        signedIn = signedIn,
        snapshot = snapshotOverride,
        savedShowsSnapshot = savedShowsSnapshotOverride,
        message = null,
        scopedShowIds = scopedShowIds,
        onOpenProfile = onOpenProfile,
        onOpenShow = onOpenShow,
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
    scopedShowIds: List<Int>,
    onOpenProfile: () -> Unit,
    onOpenShow: (Int) -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
    onClearMessage: () -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            "Favorites",
            style = MaterialTheme.typography.headlineLarge,
            color = LaughTrackColors.Foreground,
        )

        if (message != null) {
            AssistChip(
                onClick = onClearMessage,
                label = { Text(message.orEmpty()) },
            )
        }
        if (snapshot.errorMessage != null) {
            AssistChip(
                onClick = {},
                label = { Text(snapshot.errorMessage.orEmpty()) },
            )
        }

        if (signedIn) {
            SignedInLibrary(
                snapshot = snapshot,
                savedShowsSnapshot = savedShowsSnapshot,
                scopedShowIds = scopedShowIds,
                onOpenShow = onOpenShow,
                onRetrySavedShows = onRetrySavedShows,
                onToggleComedian = onToggleComedian,
                onToggleClub = onToggleClub,
                onTogglePodcast = onTogglePodcast,
            )
        } else {
            GuestLibraryPreview(onOpenProfile)
        }
    }
}

@Composable
private fun SignedInLibrary(
    snapshot: FavoritesSnapshot,
    savedShowsSnapshot: SavedShowsSnapshot,
    scopedShowIds: List<Int>,
    onOpenShow: (Int) -> Unit,
    onRetrySavedShows: (SavedShowPeriod) -> Unit,
    onToggleComedian: (String) -> Unit,
    onToggleClub: (Int) -> Unit,
    onTogglePodcast: (Int) -> Unit,
) {
    if (snapshot.isLoading) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
        ) {
            CircularProgressIndicator()
        }
    }

    SavedShowLibrarySection.entries.forEach { section ->
        val collection =
            when (section.period) {
                SavedShowPeriod.UPCOMING -> savedShowsSnapshot.upcoming
                SavedShowPeriod.PAST -> savedShowsSnapshot.past
            }
        SavedShowsSection(
            section = section,
            collection = collection,
            onOpenShow = onOpenShow,
            onRetry = { onRetrySavedShows(section.period) },
        )
    }

    TouringFavoritesSection(snapshot = snapshot, scopedShowIds = scopedShowIds)

    FavoriteSection(AuthenticatedLibrarySection.COMEDIANS.presentation) {
        if (snapshot.comedians.isEmpty()) {
            EmptyText("Favorite comedians to build your library.")
        } else {
            snapshot.comedians.forEach { comedian ->
                FavoriteRow(
                    title = comedian.name,
                    subtitle = "${comedian.showCount} upcoming shows",
                    isFavorite = snapshot.comedianValues[comedian.uuid] ?: true,
                    onToggle = { onToggleComedian(comedian.uuid) },
                )
            }
        }
    }

    FavoriteSection(AuthenticatedLibrarySection.CLUBS.presentation) {
        if (snapshot.clubs.isEmpty()) {
            EmptyText("Favorite clubs to keep their calendars close.")
        } else {
            snapshot.clubs.forEach { club ->
                ClubRow(club, snapshot.clubValues[club.id] ?: true) { onToggleClub(club.id) }
            }
        }
    }

    FavoriteSection(AuthenticatedLibrarySection.PODCASTS.presentation) {
        if (snapshot.podcasts.isEmpty()) {
            EmptyText("Favorite podcasts to find new episodes faster.")
        } else {
            snapshot.podcasts.forEach { podcast ->
                PodcastRow(podcast, snapshot.podcastValues[podcast.id] ?: true) {
                    onTogglePodcast(podcast.id)
                }
            }
        }
    }
}

@Composable
private fun SavedShowsSection(
    section: SavedShowLibrarySection,
    collection: SavedShowsCollection,
    onOpenShow: (Int) -> Unit,
    onRetry: () -> Unit,
) {
    FavoriteSection(section.presentation) {
        when (val state = savedShowCollectionState(collection)) {
            SavedShowCollectionPresentationState.Loading ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                ) {
                    CircularProgressIndicator()
                }

            is SavedShowCollectionPresentationState.Error -> {
                EmptyText(state.message)
                TextButton(onClick = onRetry) { Text("Retry") }
            }

            SavedShowCollectionPresentationState.Empty -> EmptyText(section.emptyMessage)
            is SavedShowCollectionPresentationState.Content ->
                state.shows.forEach { show ->
                    SavedShowRow(show = show, onOpenShow = onOpenShow)
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
private fun TouringFavoritesSection(
    snapshot: FavoritesSnapshot,
    scopedShowIds: List<Int>,
) {
    // A notification tap arrives with showIds — scope the touring section to just
    // those shows until the user chooses "Show all favorites".
    var showAll by remember { mutableStateOf(false) }
    val isScoped = scopedShowIds.isNotEmpty() && !showAll
    val touringShows =
        if (isScoped) {
            val scoped = scopedShowIds.toSet()
            snapshot.shows.filter { it.id in scoped }
        } else {
            snapshot.shows
        }
    val groupedShows = touringShows.groupByFavoriteComedian(snapshot.comedians)

    val presentation =
        AuthenticatedLibrarySection.TOURING.presentation.let { touringPresentation ->
            if (isScoped) touringPresentation.copy(title = "From your notification") else touringPresentation
        }
    FavoriteSection(presentation) {
        if (isScoped) {
            TextButton(onClick = { showAll = true }) { Text("Show all favorites") }
        }
        if (groupedShows.isEmpty()) {
            EmptyText(
                if (isScoped) {
                    "Those shows aren't in your upcoming favorites right now."
                } else {
                    "Shows from saved comedians will appear here."
                },
            )
        } else {
            groupedShows.forEach { (comedianName, shows) ->
                Text(
                    comedianName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = LaughTrackColors.Foreground,
                )
                shows.take(4).forEach { show -> ShowRow(show) }
            }
        }
    }
}

@Composable
private fun GuestLibraryPreview(onOpenProfile: () -> Unit) {
    FavoriteSection(title = "Comedy near your saved location") {
        listOf(
            "Tonight at Sample Club One" to "Headliner, feature, host",
            "Tomorrow at Sample Club Two" to "A touring comic near you",
            "Saturday at Sample Club Three" to "New saved dates land here",
        ).forEach { (title, subtitle) ->
            FavoriteRow(title = title, subtitle = subtitle, isFavorite = false, onToggle = null)
        }
    }
    FavoriteSection(title = "Saved comedians") {
        listOf("Comedian One", "Comedian Two", "Comedian Three").forEach { name ->
            FavoriteRow(title = name, subtitle = "Sign in to save", isFavorite = false, onToggle = null)
        }
    }
    Button(onClick = onOpenProfile, modifier = Modifier.fillMaxWidth()) {
        Text("Sign in to see your favorites")
    }
}

@Composable
private fun FavoriteSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit,
) = FavoriteSection(
    presentation = LibrarySectionPresentation(eyebrow = "", title = title, subtitle = ""),
    content = content,
)

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
private fun FavoriteRow(
    title: String,
    subtitle: String,
    isFavorite: Boolean,
    onToggle: (() -> Unit)?,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
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
        if (onToggle != null) {
            TextButton(onClick = onToggle) {
                Text(if (isFavorite) "Favorited" else "Favorite")
            }
        }
    }
}

@Composable
private fun ShowRow(show: Show) {
    FavoriteRow(
        title = show.name ?: show.clubName ?: "Comedy show",
        subtitle = favoriteShowSubtitle(show),
        isFavorite = true,
        onToggle = null,
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
    isFavorite: Boolean,
    onToggle: () -> Unit,
) {
    FavoriteRow(
        title = club.name,
        subtitle = "Club",
        isFavorite = isFavorite,
        onToggle = onToggle,
    )
}

@Composable
private fun PodcastRow(
    podcast: FavoritePodcastItem,
    isFavorite: Boolean,
    onToggle: () -> Unit,
) {
    FavoriteRow(
        title = podcast.title,
        subtitle = "${podcast.episodeCount} episodes",
        isFavorite = isFavorite,
        onToggle = onToggle,
    )
}

@Composable
private fun EmptyText(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

private fun List<Show>.groupByFavoriteComedian(comedians: List<ComedianSearchItem>): Map<String, List<Show>> {
    val namesByUuid = comedians.associate { it.uuid to it.name }
    val groups = linkedMapOf<String, MutableList<Show>>()
    forEach { show ->
        val matchingName =
            show.lineup
                ?.firstNotNullOfOrNull { lineup -> namesByUuid[lineup.uuid] }
                ?: "Favorite comedians"
        groups.getOrPut(matchingName) { mutableListOf() }.add(show)
    }
    return groups
}
