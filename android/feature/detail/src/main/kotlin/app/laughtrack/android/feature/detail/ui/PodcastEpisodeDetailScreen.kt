package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisodeAppearance
import app.laughtrack.android.core.network.generated.model.PodcastDetailHost
import app.laughtrack.android.core.network.generated.model.PodcastEpisodeDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.ui.components.AdaptiveDetailCatalogLayout
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.util.openUrl
import java.util.Locale

internal const val PODCAST_EPISODE_DETAIL_TEST_TAG = "podcastEpisodeDetail"
internal const val PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG = "podcastEpisodeDetailPrimaryAction"
internal const val PODCAST_EPISODE_PODCAST_LINK_TEST_TAG = "podcastEpisodeDetailPodcastLink"

internal fun podcastEpisodeComedianTestTag(id: Int): String = "podcastEpisodeDetailComedian-$id"

internal fun podcastEpisodeRowTestTag(id: Int): String = "podcastEpisodeRow-$id"

internal fun podcastEpisodePlayTestTag(id: Int): String = "podcastEpisodePlay-$id"

internal data class PodcastEpisodeDetailLineup(
    val hosts: List<PodcastDetailHost>,
    val guests: List<PodcastDetailEpisodeAppearance>,
)

internal sealed interface PodcastEpisodeDetailPrimaryAction {
    data class Play(
        val item: PodcastPlaybackItem,
    ) : PodcastEpisodeDetailPrimaryAction

    data class OpenOriginal(
        val url: String,
    ) : PodcastEpisodeDetailPrimaryAction

    data object Unavailable : PodcastEpisodeDetailPrimaryAction
}

internal fun podcastEpisodeDetailLineup(response: PodcastEpisodeDetailResponse): PodcastEpisodeDetailLineup {
    val hostIds = response.podcast.hosts.mapTo(mutableSetOf()) { it.id }
    val hostUuids = response.podcast.hosts.mapTo(mutableSetOf()) { it.uuid }
    return PodcastEpisodeDetailLineup(
        hosts = response.podcast.hosts,
        guests =
            response.episode.appearances.filter {
                it.id !in hostIds && it.uuid !in hostUuids
            },
    )
}

internal fun podcastEpisodeDetailPrimaryAction(
    response: PodcastEpisodeDetailResponse,
): PodcastEpisodeDetailPrimaryAction {
    val audioUrl = response.episode.audioUrl?.trim()?.takeIf(String::isNotEmpty)
    if (audioUrl != null) {
        return PodcastEpisodeDetailPrimaryAction.Play(
            PodcastPlaybackItem(
                episodeId = response.episode.id,
                podcastId = response.podcast.id,
                podcastTitle = response.podcast.title,
                episodeTitle = response.episode.title,
                audioUrl = audioUrl,
                artworkUrl = response.podcast.imageUrl,
            ),
        )
    }

    val episodeUrl = response.episode.episodeUrl?.trim()?.takeIf(String::isNotEmpty)
    return if (episodeUrl != null) {
        PodcastEpisodeDetailPrimaryAction.OpenOriginal(episodeUrl)
    } else {
        PodcastEpisodeDetailPrimaryAction.Unavailable
    }
}

@Composable
fun PodcastEpisodeDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: PodcastEpisodeDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()

    Box(
        Modifier
            .fillMaxSize()
            .testTag(PODCAST_EPISODE_DETAIL_TEST_TAG),
    ) {
        when (val uiState = state) {
            is UiState.Failure ->
                DetailError(
                    onRetry = viewModel::retry,
                    modifier = Modifier.fillMaxSize(),
                )
            is UiState.Success ->
                PodcastEpisodeDetailBody(
                    response = uiState.value,
                    onBack = onBack,
                    onOpenEntity = onOpenEntity,
                    onPlay = viewModel::play,
                )
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun PodcastEpisodeDetailBody(
    response: PodcastEpisodeDetailResponse,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    val context = LocalContext.current
    val lineup = podcastEpisodeDetailLineup(response)

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 28.dp),
    ) {
        AdaptiveDetailCatalogLayout(
            hero = {
                PodcastEpisodeHero(
                    response = response,
                    onBack = onBack,
                )
            },
            content = {
                Column(
                    Modifier.padding(horizontal = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp),
                ) {
                    PodcastEpisodeContext(
                        response = response,
                        onOpenPodcast = {
                            onOpenEntity(AppRoute.PodcastDetail(response.podcast.id))
                        },
                    )
                    PodcastEpisodePrimaryAction(
                        action = podcastEpisodeDetailPrimaryAction(response),
                        onPlay = onPlay,
                        onOpenOriginal = context::openUrl,
                    )
                    response.episode.description
                        ?.trim()
                        ?.takeIf(String::isNotEmpty)
                        ?.let { PodcastEpisodeDescription(it) }
                    if (lineup.hosts.isNotEmpty()) {
                        PodcastEpisodePeople(
                            eyebrow = "Featuring",
                            title = if (lineup.hosts.size == 1) "Host" else "Hosts",
                            people = lineup.hosts.map { EpisodePerson(it.id, it.name, it.imageUrl) },
                            onOpenComedian = {
                                onOpenEntity(AppRoute.ComedianDetail(it))
                            },
                        )
                    }
                    if (lineup.guests.isNotEmpty()) {
                        PodcastEpisodePeople(
                            eyebrow = "Featuring",
                            title = if (lineup.guests.size == 1) "Guest" else "Guests",
                            people = lineup.guests.map { EpisodePerson(it.id, it.name, it.imageUrl) },
                            onOpenComedian = {
                                onOpenEntity(AppRoute.ComedianDetail(it))
                            },
                        )
                    }
                }
            },
        )
    }
}

@Composable
private fun PodcastEpisodeHero(
    response: PodcastEpisodeDetailResponse,
    onBack: () -> Unit,
) {
    Box(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    listOf(Color(0xFF70451F), Color(0xFF321B13), LaughTrackColors.Canvas),
                ),
            ),
    ) {
        Surface(
            onClick = onBack,
            shape = CircleShape,
            color = LaughTrackColors.Surface.copy(alpha = 0.94f),
            modifier =
                Modifier
                    .statusBarsPadding()
                    .padding(start = 16.dp, top = 24.dp)
                    .size(40.dp),
        ) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
        }

        Column(
            Modifier
                .fillMaxWidth()
                .padding(top = 118.dp, start = 20.dp, end = 20.dp, bottom = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = response.podcast.title.uppercase(Locale.US),
                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold),
                color = LaughTrackColors.AccentStrong,
                textAlign = TextAlign.Center,
            )
            Text(
                text = response.episode.title,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
                textAlign = TextAlign.Center,
                maxLines = 4,
                overflow = TextOverflow.Ellipsis,
            )
            RemoteImage(
                url = response.podcast.imageUrl,
                contentDescription = response.podcast.title,
                modifier =
                    Modifier
                        .size(180.dp)
                        .clip(RoundedCornerShape(18.dp))
                        .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(18.dp)),
                contentScale = ContentScale.Crop,
                fallback = RemoteImageFallback.Podcast,
            )
        }
    }
}

@Composable
private fun PodcastEpisodeContext(
    response: PodcastEpisodeDetailResponse,
    onOpenPodcast: () -> Unit,
) {
    EpisodeCard {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            EpisodeSectionHeader(eyebrow = "Episode", title = podcastEpisodeMetadata(response.episode))
            Surface(
                onClick = onOpenPodcast,
                color = Color.Transparent,
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .testTag(PODCAST_EPISODE_PODCAST_LINK_TEST_TAG)
                        .semantics {
                            contentDescription = "Open podcast ${response.podcast.title}"
                        },
            ) {
                Row(
                    Modifier.padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RemoteImage(
                        url = response.podcast.imageUrl,
                        contentDescription = null,
                        modifier = Modifier.size(44.dp).clip(RoundedCornerShape(8.dp)),
                        fallback = RemoteImageFallback.Podcast,
                    )
                    Text(
                        response.podcast.title,
                        style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold),
                        color = LaughTrackColors.Foreground,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(
                        Icons.Filled.ChevronRight,
                        contentDescription = null,
                        tint = LaughTrackColors.ForegroundMuted,
                    )
                }
            }
        }
    }
}

@Composable
private fun PodcastEpisodePrimaryAction(
    action: PodcastEpisodeDetailPrimaryAction,
    onPlay: (PodcastPlaybackItem) -> Unit,
    onOpenOriginal: (String?) -> Unit,
) {
    when (action) {
        is PodcastEpisodeDetailPrimaryAction.Play ->
            Button(
                onClick = { onPlay(action.item) },
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .testTag(PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG)
                        .semantics { contentDescription = "Play episode" },
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = null)
                Text("Play episode", Modifier.padding(start = 8.dp))
            }
        is PodcastEpisodeDetailPrimaryAction.OpenOriginal ->
            Button(
                onClick = { onOpenOriginal(action.url) },
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .testTag(PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG)
                        .semantics { contentDescription = "Open original episode" },
            ) {
                Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null)
                Text("Open original episode", Modifier.padding(start = 8.dp))
            }
        PodcastEpisodeDetailPrimaryAction.Unavailable ->
            PodcastEpisodeUnavailable()
    }
}

@Composable
private fun PodcastEpisodeUnavailable() {
    EpisodeCard(
        modifier =
            Modifier
                .testTag(PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG)
                .semantics { contentDescription = "Playback unavailable" },
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                "Playback unavailable",
                fontWeight = FontWeight.SemiBold,
                color = LaughTrackColors.Foreground,
            )
            Text(
                "This episode has metadata, but no audio or original episode link.",
                style = MaterialTheme.typography.bodySmall,
                color = LaughTrackColors.ForegroundMuted,
            )
        }
    }
}

@Composable
private fun PodcastEpisodeDescription(description: String) {
    EpisodeCard {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            EpisodeSectionHeader(eyebrow = "Episode notes", title = "About this episode")
            Text(
                description,
                style = MaterialTheme.typography.bodyMedium,
                color = LaughTrackColors.Foreground,
            )
        }
    }
}

private data class EpisodePerson(
    val id: Int,
    val name: String,
    val imageUrl: String?,
)

@Composable
private fun PodcastEpisodePeople(
    eyebrow: String,
    title: String,
    people: List<EpisodePerson>,
    onOpenComedian: (Int) -> Unit,
) {
    EpisodeCard {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            EpisodeSectionHeader(eyebrow = eyebrow, title = title)
            people.forEach { person ->
                Surface(
                    onClick = { onOpenComedian(person.id) },
                    color = Color.Transparent,
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .testTag(podcastEpisodeComedianTestTag(person.id))
                            .semantics {
                                contentDescription = "Open comedian ${person.name}"
                            },
                ) {
                    Row(
                        Modifier.padding(vertical = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RemoteImage(
                            url = person.imageUrl,
                            contentDescription = null,
                            modifier = Modifier.size(44.dp).clip(CircleShape),
                            fallback = RemoteImageFallback.Person,
                        )
                        Text(
                            person.name,
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold),
                            color = LaughTrackColors.Foreground,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Icon(
                            Icons.Filled.ChevronRight,
                            contentDescription = null,
                            tint = LaughTrackColors.ForegroundMuted,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun EpisodeCard(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    Surface(
        color = LaughTrackColors.SurfaceMuted,
        shape = RoundedCornerShape(16.dp),
        modifier =
            modifier
                .fillMaxWidth()
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(16.dp)),
    ) {
        Box(Modifier.padding(16.dp)) { content() }
    }
}

@Composable
private fun EpisodeSectionHeader(
    eyebrow: String,
    title: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            eyebrow.uppercase(Locale.US),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = LaughTrackColors.AccentStrong,
        )
        Text(
            title,
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            color = LaughTrackColors.Foreground,
        )
    }
}
