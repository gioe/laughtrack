package app.laughtrack.android.feature.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeRecommendation
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import kotlin.math.roundToInt

internal fun homePodcastEpisodeRowTestTag(id: Int): String = "homePodcastEpisode-$id"

internal fun homePodcastEpisodePlayTestTag(id: Int): String = "homePodcastEpisodePlay-$id"

internal data class HomePodcastEpisodeDiscoveryItem(
    val id: Int,
    val title: String,
    val podcastId: Int,
    val podcastTitle: String,
    val artworkUrl: String?,
    val releaseMetadata: String,
    val comedianName: String,
    val comedianRole: String,
    val recommendationReason: String,
    val playbackItem: PodcastPlaybackItem?,
)

internal sealed interface HomePodcastRailContent {
    data class Episodes(
        val episodes: List<HomeFeedPodcastEpisode>,
    ) : HomePodcastRailContent

    data class LegacyPodcasts(
        val podcasts: List<HomeFeedPodcast>,
    ) : HomePodcastRailContent
}

internal fun homePodcastRailContent(
    episodes: List<HomeFeedPodcastEpisode>?,
    podcasts: List<HomeFeedPodcast>,
): HomePodcastRailContent {
    val uniqueEpisodes = episodes.orEmpty().distinctBy { it.id }
    return if (uniqueEpisodes.isNotEmpty()) {
        HomePodcastRailContent.Episodes(uniqueEpisodes)
    } else {
        HomePodcastRailContent.LegacyPodcasts(podcasts.distinctBy { it.id })
    }
}

internal fun homePodcastEpisodeDiscoveryItem(
    episode: HomeFeedPodcastEpisode,
    today: LocalDate = LocalDate.now(),
): HomePodcastEpisodeDiscoveryItem {
    val recommendation = episode.recommendation
    val audioUrl = episode.audioUrl?.trim()?.takeIf { it.isNotEmpty() }
    return HomePodcastEpisodeDiscoveryItem(
        id = episode.id,
        title = episode.title,
        podcastId = episode.podcast.id,
        podcastTitle = episode.podcast.title,
        artworkUrl = episode.podcast.imageUrl,
        releaseMetadata = homePodcastEpisodeReleaseMetadata(episode, today),
        comedianName = recommendation.comedian.name,
        comedianRole = homePodcastEpisodeRoleLabel(recommendation.appearanceRole),
        recommendationReason = homePodcastEpisodeReasonLabel(recommendation),
        playbackItem =
            audioUrl?.let {
                PodcastPlaybackItem(
                    episodeId = episode.id,
                    podcastId = episode.podcast.id,
                    podcastTitle = episode.podcast.title,
                    episodeTitle = episode.title,
                    audioUrl = it,
                    artworkUrl = episode.podcast.imageUrl,
                )
            },
    )
}

internal fun homePodcastEpisodeRoute(item: HomePodcastEpisodeDiscoveryItem): AppRoute =
    AppRoute.PodcastEpisodeDetail(item.id)

private fun homePodcastEpisodeReleaseMetadata(
    episode: HomeFeedPodcastEpisode,
    today: LocalDate,
): String {
    val releaseDate = parsePodcastEpisodeDate(episode.releaseDate)
    val freshness =
        releaseDate?.let { date ->
            when (val days = ChronoUnit.DAYS.between(date, today).coerceAtLeast(0)) {
                0L -> "Today"
                1L -> "Yesterday"
                in 2L..6L -> "${days}d ago"
                else -> date.format(PODCAST_DATE_FORMATTER)
            }
        } ?: "Episode"
    val duration =
        episode.durationSeconds
            ?.takeIf { it > 0 }
            ?.let { seconds -> "${(seconds / 60.0).roundToInt().coerceAtLeast(1)} min" }
    return listOfNotNull(freshness, duration).joinToString(" • ")
}

private fun parsePodcastEpisodeDate(raw: String): LocalDate? =
    runCatching { LocalDate.parse(raw) }.getOrNull()
        ?: runCatching { OffsetDateTime.parse(raw).toLocalDate() }.getOrNull()

private fun homePodcastEpisodeRoleLabel(role: HomeFeedPodcastEpisodeRecommendation.AppearanceRole): String =
    when (role) {
        HomeFeedPodcastEpisodeRecommendation.AppearanceRole.HOST -> "Host"
        HomeFeedPodcastEpisodeRecommendation.AppearanceRole.COHOST -> "Cohost"
        HomeFeedPodcastEpisodeRecommendation.AppearanceRole.GUEST -> "Guest"
    }

private fun homePodcastEpisodeReasonLabel(recommendation: HomeFeedPodcastEpisodeRecommendation): String {
    val comedian = recommendation.comedian.name
    return when (recommendation.reason) {
        HomeFeedPodcastEpisodeRecommendation.Reason.FOLLOWED_COMEDIAN -> "Because you follow $comedian"
        HomeFeedPodcastEpisodeRecommendation.Reason.FAVORITE_PODCAST -> "From a favorite podcast"
        HomeFeedPodcastEpisodeRecommendation.Reason.GUEST_APPEARANCE -> "Guest appearance by $comedian"
        HomeFeedPodcastEpisodeRecommendation.Reason.POPULAR_COMEDIAN -> "Featuring popular comedian $comedian"
        HomeFeedPodcastEpisodeRecommendation.Reason.RECENT_EPISODE -> "A recent episode with $comedian"
    }
}

@Composable
internal fun HomePodcastRail(
    episodes: List<HomeFeedPodcastEpisode>?,
    podcasts: List<HomeFeedPodcast>,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onBrowsePodcasts: () -> Unit,
) {
    when (val content = homePodcastRailContent(episodes, podcasts)) {
        is HomePodcastRailContent.Episodes ->
            HomePodcastEpisodeDiscoveryRail(
                episodes = content.episodes,
                onOpenEntity = onOpenEntity,
                onPlay = onPlay,
                onBrowsePodcasts = onBrowsePodcasts,
            )
        is HomePodcastRailContent.LegacyPodcasts ->
            HomeLegacyPodcastRail(
                podcasts = content.podcasts,
                onOpenEntity = onOpenEntity,
                onBrowsePodcasts = onBrowsePodcasts,
            )
    }
}

@Composable
internal fun HomePodcastEpisodeDiscoveryRail(
    episodes: List<HomeFeedPodcastEpisode>,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onBrowsePodcasts: () -> Unit,
) {
    FeedRailCard(
        eyebrow = "Funny listening",
        title = "Episodes for you",
        emptyMessage = "No podcast episodes found.",
        itemCount = episodes.size,
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            episodes.forEach { episode ->
                val item = homePodcastEpisodeDiscoveryItem(episode)
                HomePodcastEpisodeDiscoveryRow(
                    item = item,
                    onOpen = { onOpenEntity(homePodcastEpisodeRoute(item)) },
                    onPlay = item.playbackItem?.let { playbackItem -> { onPlay(playbackItem) } },
                )
            }
        }
        SeeAllButton(label = "Browse podcasts", onClick = onBrowsePodcasts)
    }
}

@Composable
private fun HomeLegacyPodcastRail(
    podcasts: List<HomeFeedPodcast>,
    onOpenEntity: (AppRoute) -> Unit,
    onBrowsePodcasts: () -> Unit,
) {
    FeedRailCard(title = "Comedy podcasts", emptyMessage = "No podcasts found.", itemCount = podcasts.size) {
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(podcasts, key = { it.id }) { podcast ->
                FeedCard(
                    title = podcast.title,
                    subtitle = podcast.authorName ?: "${podcast.episodeCount} episodes",
                    imageUrl = podcast.imageUrl,
                    fallback = RemoteImageFallback.Podcast,
                    width = 168.dp,
                    onClick = { onOpenEntity(AppRoute.PodcastDetail(podcast.id)) },
                )
            }
        }
        SeeAllButton(label = "Browse podcasts", onClick = onBrowsePodcasts)
    }
}

@Composable
private fun HomePodcastEpisodeDiscoveryRow(
    item: HomePodcastEpisodeDiscoveryItem,
    onOpen: () -> Unit,
    onPlay: (() -> Unit)?,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(LaughTrackColors.Surface)
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(14.dp))
                .padding(10.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            modifier =
                Modifier
                    .weight(1f)
                    .testTag(homePodcastEpisodeRowTestTag(item.id))
                    .clickable(onClick = onOpen)
                    .semantics {
                        contentDescription =
                            "Open ${item.title}, ${item.podcastTitle}, ${item.releaseMetadata}, " +
                            "${item.comedianRole} ${item.comedianName}, ${item.recommendationReason}"
                    },
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.Top,
        ) {
            RemoteImage(
                url = item.artworkUrl,
                contentDescription = item.podcastTitle,
                modifier = Modifier.size(68.dp).clip(RoundedCornerShape(10.dp)),
                fallback = RemoteImageFallback.Podcast,
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    item.podcastTitle,
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = LaughTrackColors.AccentStrong,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    item.title,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = LaughTrackColors.Foreground,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    item.releaseMetadata,
                    style = MaterialTheme.typography.labelSmall,
                    color = LaughTrackColors.ForegroundMuted,
                )
                Text(
                    "${item.comedianRole}: ${item.comedianName}",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                    color = LaughTrackColors.Foreground,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    item.recommendationReason,
                    style = MaterialTheme.typography.labelSmall,
                    color = LaughTrackColors.ForegroundMuted,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        if (onPlay != null) {
            IconButton(
                onClick = onPlay,
                modifier = Modifier.testTag(homePodcastEpisodePlayTestTag(item.id)),
            ) {
                Icon(
                    Icons.Filled.PlayArrow,
                    contentDescription = "Play episode ${item.title}",
                    tint = LaughTrackColors.AccentStrong,
                )
            }
        }
    }
}

private val PODCAST_DATE_FORMATTER = DateTimeFormatter.ofPattern("MMM d", Locale.US)
