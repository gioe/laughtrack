@file:Suppress("FunctionName")

package app.laughtrack.android.feature.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonBox
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.ui.HomeUiState
import app.laughtrack.android.feature.home.ui.HomeViewModel

/** Discover/Home surface backed by the composite home feed endpoint. */
@Composable
fun HomeScreen(
    onOpenEntity: (AppRoute) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    when (state.feed) {
        is UiState.Failure -> HomeError(onRetry = viewModel::retry, modifier = modifier)
        is UiState.Success -> HomeContent(state = state, onOpenEntity = onOpenEntity, modifier = modifier)
        else -> HomeLoading(modifier)
    }
}

@Composable
private fun HomeContent(
    state: HomeUiState,
    onOpenEntity: (AppRoute) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        item {
            Text("Discover", style = MaterialTheme.typography.headlineLarge)
        }
        item {
            LocationPrompt(title = state.locationTitle, subtitle = state.locationSubtitle)
        }
        item {
            ShowRail(
                title = "Tonight near you",
                shows = state.showsTonight,
                onOpenEntity = onOpenEntity,
            )
        }
        item {
            ShowRail(
                title = "Trending this week",
                shows = state.trendingThisWeek,
                onOpenEntity = onOpenEntity,
            )
        }
        item {
            ComedianRail(state.comedians, onOpenEntity)
        }
        item {
            ClubRail(state.clubs, onOpenEntity)
        }
        item {
            PodcastRail(state.podcasts, onOpenEntity)
        }
    }
}

@Composable
private fun LocationPrompt(
    title: String,
    subtitle: String,
) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceContainerHigh,
        shape = RoundedCornerShape(8.dp),
        tonalElevation = 2.dp,
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(
                subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ShowRail(
    title: String,
    shows: List<Show>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRail(title = title, emptyMessage = "No shows found for this rail.", itemCount = shows.size) {
        items(shows) { show ->
            FeedCard(
                title = show.name ?: "Show",
                subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" · ").ifBlank { null },
                imageUrl = show.imageUrl,
                width = 240.dp,
                onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
            )
        }
    }
}

@Composable
private fun ComedianRail(
    comedians: List<ComedianListItem>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRail(title = "Comedians to watch", emptyMessage = "No comedians found.", itemCount = comedians.size) {
        items(comedians) { comedian ->
            FeedCard(
                title = comedian.name,
                subtitle = "${comedian.showCount} shows",
                imageUrl = comedian.imageUrl,
                width = 180.dp,
                onClick = { onOpenEntity(AppRoute.ComedianDetail(comedian.id)) },
            )
        }
    }
}

@Composable
private fun ClubRail(
    clubs: List<ClubListItem>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRail(title = "Popular clubs", emptyMessage = "No clubs found.", itemCount = clubs.size) {
        items(clubs) { club ->
            FeedCard(
                title = club.name,
                subtitle = club.address,
                imageUrl = club.imageUrl,
                width = 200.dp,
                onClick = { onOpenEntity(AppRoute.ClubDetail(club.id)) },
            )
        }
    }
}

@Composable
private fun PodcastRail(
    podcasts: List<HomeFeedPodcast>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    FeedRail(title = "Comedy podcasts", emptyMessage = "No podcasts found.", itemCount = podcasts.size) {
        items(podcasts) { podcast ->
            FeedCard(
                title = podcast.title,
                subtitle = podcast.authorName ?: "${podcast.episodeCount} episodes",
                imageUrl = podcast.imageUrl,
                width = 200.dp,
                onClick = { onOpenEntity(AppRoute.PodcastDetail(podcast.id)) },
            )
        }
    }
}

@Composable
private fun FeedRail(
    title: String,
    emptyMessage: String,
    itemCount: Int,
    content: LazyListScope.() -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        if (itemCount == 0) {
            Text(
                emptyMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                content()
            }
        }
    }
}

@Composable
private fun FeedCard(
    title: String,
    subtitle: String?,
    imageUrl: String?,
    width: Dp,
    onClick: () -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .size(width = width, height = 180.dp)
                .clip(RoundedCornerShape(8.dp))
                .clickable(onClick = onClick),
        color = MaterialTheme.colorScheme.surfaceContainer,
        shape = RoundedCornerShape(8.dp),
    ) {
        Column {
            RemoteImage(
                url = imageUrl,
                contentDescription = title,
                modifier = Modifier.fillMaxWidth().height(112.dp),
            )
            Column(
                Modifier.padding(12.dp),
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
                        maxLines = 1,
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
