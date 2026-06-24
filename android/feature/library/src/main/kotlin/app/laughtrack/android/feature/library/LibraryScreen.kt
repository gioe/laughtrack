package app.laughtrack.android.feature.library

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.Show

@Composable
fun LibraryScreen(
    signedIn: Boolean,
    onOpenProfile: () -> Unit,
    viewModel: LibraryViewModel = hiltViewModel(),
) {
    val snapshot by viewModel.snapshot.collectAsState()
    val message by viewModel.message.collectAsState()

    LaunchedEffect(signedIn) {
        viewModel.refresh(signedIn)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Favorites", style = MaterialTheme.typography.headlineLarge)

        if (message != null) {
            AssistChip(
                onClick = viewModel::clearMessage,
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
                onToggleComedian = viewModel::toggleComedian,
                onToggleClub = viewModel::toggleClub,
                onTogglePodcast = viewModel::togglePodcast,
            )
        } else {
            GuestLibraryPreview(onOpenProfile)
        }
    }
}

@Composable
private fun SignedInLibrary(
    snapshot: FavoritesSnapshot,
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

    val groupedShows = snapshot.shows.groupByFavoriteComedian(snapshot.comedians)

    FavoriteSection(title = "Your favorites are touring") {
        if (groupedShows.isEmpty()) {
            EmptyText("Shows from saved comedians will appear here.")
        } else {
            groupedShows.forEach { (comedianName, shows) ->
                Text(
                    comedianName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                shows.take(4).forEach { show -> ShowRow(show) }
            }
        }
    }

    FavoriteSection(title = "Saved comedians") {
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

    FavoriteSection(title = "Saved clubs") {
        if (snapshot.clubs.isEmpty()) {
            EmptyText("Favorite clubs to keep their calendars close.")
        } else {
            snapshot.clubs.forEach { club ->
                ClubRow(club, snapshot.clubValues[club.id] ?: true) { onToggleClub(club.id) }
            }
        }
    }

    FavoriteSection(title = "Saved podcasts") {
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
private fun FavoriteSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        Card(modifier = Modifier.fillMaxWidth()) {
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
        subtitle = listOfNotNull(show.clubName, show.clubCity, show.date).joinToString(" - "),
        isFavorite = true,
        onToggle = null,
    )
}

@Composable
private fun ClubRow(club: FavoriteClubItem, isFavorite: Boolean, onToggle: () -> Unit) {
    FavoriteRow(
        title = club.name,
        subtitle = "Club",
        isFavorite = isFavorite,
        onToggle = onToggle,
    )
}

@Composable
private fun PodcastRow(podcast: FavoritePodcastItem, isFavorite: Boolean, onToggle: () -> Unit) {
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

private fun List<Show>.groupByFavoriteComedian(
    comedians: List<ComedianSearchItem>,
): Map<String, List<Show>> {
    val namesByUuid = comedians.associate { it.uuid to it.name }
    val groups = linkedMapOf<String, MutableList<Show>>()
    forEach { show ->
        val matchingName = show.lineup
            ?.firstNotNullOfOrNull { lineup -> namesByUuid[lineup.uuid] }
            ?: "Favorite comedians"
        groups.getOrPut(matchingName) { mutableListOf() }.add(show)
    }
    return groups
}
