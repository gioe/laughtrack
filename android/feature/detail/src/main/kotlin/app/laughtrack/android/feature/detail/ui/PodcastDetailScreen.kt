package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisode
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailHero
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.DetailScaffold
import app.laughtrack.android.feature.detail.ui.components.EntityAvatar
import app.laughtrack.android.feature.detail.ui.components.SectionHeader
import app.laughtrack.android.feature.detail.util.formatEpisodeDuration
import app.laughtrack.android.feature.detail.util.formatReleaseDate
import app.laughtrack.android.feature.detail.util.shareLink

@Composable
fun PodcastDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: PodcastDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val data = (state as? UiState.Success)?.value

    DetailScaffold(
        title = data?.podcast?.title ?: "Podcast",
        onBack = onBack,
        onShare = data?.let { loaded -> { context.shareLink(loaded.podcast.websiteUrl, loaded.podcast.title) } },
    ) { modifier ->
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = modifier)
            is UiState.Success -> PodcastDetailBody(data!!, modifier, onOpenEntity, viewModel::play)
            else -> DetailLoading(modifier)
        }
    }
}

@Composable
private fun PodcastDetailBody(
    data: PodcastDetailResponse,
    modifier: Modifier,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    val podcast = data.podcast
    Column(
        modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        DetailHero(url = podcast.imageUrl, contentDescription = podcast.title)
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(podcast.title, style = MaterialTheme.typography.headlineSmall)
            podcast.authorName?.takeIf { it.isNotBlank() }?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            podcast.description?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = MaterialTheme.typography.bodyMedium)
            }
        }

        PodcastRelatedRow(data, onOpenEntity)

        SectionHeader("Episodes", Modifier.padding(horizontal = 16.dp))
        if (data.episodes.isEmpty()) {
            Text(
                "No episodes yet.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        } else {
            data.episodes.forEach { episode -> EpisodeRow(podcast, episode, onPlay) }
        }
    }
}

@Composable
private fun PodcastRelatedRow(
    data: PodcastDetailResponse,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (data.relatedComedians.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeader("Related comedians", Modifier.padding(horizontal = 16.dp))
        LazyRow(
            contentPadding = PaddingValues(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(data.relatedComedians) { comedian ->
                EntityAvatar(
                    name = comedian.name,
                    imageUrl = comedian.imageUrl,
                    subtitle = "${comedian.showCount} shows",
                    onClick = { onOpenEntity(AppRoute.ComedianDetail(comedian.id)) },
                )
            }
        }
    }
}

@Composable
private fun EpisodeRow(
    podcast: PodcastDetailPodcast,
    episode: PodcastDetailEpisode,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    val playbackItem = episode.playbackItem(podcast)
    val meta =
        listOfNotNull(
            formatReleaseDate(episode.releaseDate),
            formatEpisodeDuration(episode.durationSeconds),
        ).joinToString(" · ").ifBlank { null }
    Column(
        Modifier
            .fillMaxWidth()
            .then(if (playbackItem != null) Modifier.clickable { onPlay(playbackItem) } else Modifier)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(
            episode.title,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        meta?.let {
            Text(it, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        OutlinedButton(
            onClick = { playbackItem?.let(onPlay) },
            enabled = playbackItem != null,
        ) {
            Text("Play")
        }
    }
}

private fun PodcastDetailEpisode.playbackItem(podcast: PodcastDetailPodcast): PodcastPlaybackItem? {
    val audio = audioUrl?.takeIf { it.isNotBlank() } ?: return null
    return PodcastPlaybackItem(
        episodeId = id,
        podcastId = podcast.id,
        podcastTitle = podcast.title,
        episodeTitle = title,
        audioUrl = audio,
        artworkUrl = podcast.imageUrl,
    )
}
