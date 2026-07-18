package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.NorthEast
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Sensors
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisode
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisodeAppearance
import app.laughtrack.android.core.network.generated.model.PodcastDetailHost
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.util.openUrl
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

private const val PODCAST_EPISODE_PAGE_SIZE = 10
private val PodcastStage = Color(0xFF211916)

@Composable
fun PodcastDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: PodcastDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val favoritesSnapshot by viewModel.favoritesSnapshot.collectAsStateWithLifecycle()

    Box(Modifier.fillMaxSize()) {
        when (val uiState = state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success -> {
                val podcast = uiState.value.podcast
                val isFavorite = favoritesSnapshot.podcastValues[podcast.id] ?: (podcast.isFavorite == true)
                PodcastDetailBody(
                    data = uiState.value,
                    isFavorite = isFavorite,
                    isFavoritePending = viewModel.isFavoritePending(podcast.id),
                    onFavorite = { viewModel.toggleFavorite(podcast.id, isFavorite) },
                    onBack = onBack,
                    onOpenEntity = onOpenEntity,
                    onPlay = viewModel::play,
                )
            }
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun PodcastDetailBody(
    data: PodcastDetailResponse,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 28.dp),
    ) {
        PodcastMarqueeHero(
            podcast = data.podcast,
            isFavorite = isFavorite,
            isFavoritePending = isFavoritePending,
            onFavorite = onFavorite,
            onBack = onBack,
            onOpenEntity = onOpenEntity,
        )

        Column(
            Modifier.padding(horizontal = 8.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            PodcastEpisodeSection(
                podcast = data.podcast,
                episodes = data.episodes,
                onOpenEntity = onOpenEntity,
                onPlay = onPlay,
            )

            PodcastFrequentGuestsSection(
                guests = frequentPodcastGuests(data),
                onOpenEntity = onOpenEntity,
            )
        }
    }
}

@Composable
private fun PodcastMarqueeHero(
    podcast: PodcastDetailPodcast,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
) {
    val context = LocalContext.current
    Box(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.radialGradient(
                    colors =
                        listOf(
                            LaughTrackColors.Highlight.copy(alpha = 0.18f),
                            Color.Transparent,
                        ),
                    radius = 900f,
                ),
            ),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            PodcastChromeButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            PodcastChromeButton(onClick = onFavorite, enabled = !isFavoritePending) {
                Icon(
                    imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                    contentDescription = if (isFavorite) "Remove favorite" else "Favorite",
                    tint = if (isFavorite) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                )
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
                text = podcast.title.uppercase(Locale.US),
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
                textAlign = TextAlign.Center,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            PodcastCoverStage(url = podcast.imageUrl)
            PodcastHeroActions(
                websiteUrl = podcast.websiteUrl,
                feedUrl = podcast.feedUrl,
                openUrl = context::openUrl,
            )
            PodcastHosts(hosts = podcast.hosts, onOpenEntity = onOpenEntity)
        }
    }
}

@Composable
private fun PodcastChromeButton(
    onClick: () -> Unit,
    enabled: Boolean = true,
    content: @Composable () -> Unit,
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = CircleShape,
        color = LaughTrackColors.Surface.copy(alpha = 0.94f),
        modifier = Modifier.size(40.dp),
        content = {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
        },
    )
}

@Composable
private fun PodcastCoverStage(url: String?) {
    Box(
        Modifier
            .size(width = 224.dp, height = 210.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(
                Brush.radialGradient(
                    colors =
                        listOf(
                            LaughTrackColors.Highlight.copy(alpha = 0.38f),
                            PodcastStage,
                            LaughTrackColors.Surface,
                        ),
                ),
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box {
                RemoteImage(
                    url = url,
                    contentDescription = null,
                    modifier =
                        Modifier
                            .size(150.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .border(1.dp, Color.Black.copy(alpha = 0.55f), RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Crop,
                    fallback = RemoteImageFallback.Podcast,
                )
                PodcastRssBadge(Modifier.align(Alignment.TopEnd).padding(7.dp))
            }
            PodcastWaveform()
        }
    }
}

@Composable
private fun PodcastRssBadge(modifier: Modifier = Modifier) {
    Box(
        modifier
            .size(30.dp)
            .clip(CircleShape)
            .background(Color.Black.copy(alpha = 0.72f))
            .border(1.dp, LaughTrackColors.AccentStrong.copy(alpha = 0.92f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            Icons.Filled.Sensors,
            contentDescription = null,
            tint = LaughTrackColors.AccentStrong,
            modifier = Modifier.size(18.dp),
        )
    }
}

@Composable
private fun PodcastWaveform() {
    val heights = remember { listOf(8, 16, 11, 22, 13, 18, 9, 14, 7) }
    Row(
        Modifier
            .height(24.dp)
            .clip(CircleShape)
            .background(Color.Black.copy(alpha = 0.36f))
            .padding(horizontal = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            Icons.Filled.GraphicEq,
            contentDescription = null,
            tint = LaughTrackColors.AccentStrong,
            modifier = Modifier.size(16.dp),
        )
        heights.forEach { height ->
            Box(
                Modifier
                    .width(3.dp)
                    .height(height.dp)
                    .clip(CircleShape)
                    .background(LaughTrackColors.AccentStrong),
            )
        }
    }
}

@Composable
private fun PodcastHeroActions(
    websiteUrl: String?,
    feedUrl: String?,
    openUrl: (String?) -> Unit,
) {
    val actions =
        listOf(
            Triple("Website", Icons.Filled.NorthEast, websiteUrl),
            Triple("RSS", Icons.Filled.Sensors, feedUrl),
        ).filter { !it.third.isNullOrBlank() }
    if (actions.isEmpty()) return

    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        actions.forEach { (label, imageVector, url) ->
            Column(
                Modifier.clickable { openUrl(url) },
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Surface(
                    shape = CircleShape,
                    color = LaughTrackColors.Surface.copy(alpha = 0.94f),
                    modifier = Modifier.size(40.dp),
                ) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector,
                            contentDescription = null,
                            tint = LaughTrackColors.Foreground,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                }
                Text(label, style = MaterialTheme.typography.labelMedium, color = LaughTrackColors.Foreground)
            }
        }
    }
}

@Composable
private fun PodcastHosts(
    hosts: List<PodcastDetailHost>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (hosts.isEmpty()) return
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        hosts.forEach { host ->
            Column(
                Modifier
                    .width(88.dp)
                    .clickable { onOpenEntity(AppRoute.ComedianDetail(host.id)) },
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                PodcastHostArtwork(host)
                Text(
                    host.name,
                    style = MaterialTheme.typography.labelLarge,
                    color = LaughTrackColors.Foreground,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun PodcastHostArtwork(host: PodcastDetailHost) {
    Box(Modifier.size(70.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val ringRadius = size.minDimension / 2f - 2.dp.toPx()
            repeat(28) { index ->
                val angle = (2.0 * PI * index / 28.0)
                drawCircle(
                    color = LaughTrackColors.AccentStrong,
                    radius = 1.3.dp.toPx(),
                    center =
                        Offset(
                            x = center.x + (cos(angle) * ringRadius).toFloat(),
                            y = center.y + (sin(angle) * ringRadius).toFloat(),
                        ),
                )
            }
        }
        RemoteImage(
            url = host.imageUrl,
            contentDescription = host.name,
            modifier = Modifier.size(64.dp).clip(CircleShape),
            fallback = RemoteImageFallback.Person,
        )
    }
}

@Composable
private fun PodcastEpisodeSection(
    podcast: PodcastDetailPodcast,
    episodes: List<PodcastDetailEpisode>,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    val visibleEpisodes = remember(episodes) { episodes.filter { it.isPlayableOrOpenable() } }
    val pageCount = maxOf(1, (visibleEpisodes.size + PODCAST_EPISODE_PAGE_SIZE - 1) / PODCAST_EPISODE_PAGE_SIZE)
    var currentPage by rememberSaveable(podcast.id) { mutableIntStateOf(0) }
    val safePage = currentPage.coerceIn(0, pageCount - 1)
    val page =
        visibleEpisodes.drop(safePage * PODCAST_EPISODE_PAGE_SIZE).take(PODCAST_EPISODE_PAGE_SIZE)

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PodcastSectionHeader(eyebrow = "Catalog", title = "Episodes")
        when {
            episodes.isEmpty() ->
                PodcastEmptyCard(
                    "No Episodes Found",
                    "${podcast.title} has no episodes on LaughTrack yet.",
                )
            visibleEpisodes.isEmpty() ->
                PodcastEmptyCard(
                    "No playable episodes yet",
                    "LaughTrack has not matched this podcast with playable episodes yet.",
                )
            else -> {
                page.forEach { episode ->
                    PodcastEpisodeCard(
                        podcast = podcast,
                        episode = episode,
                        onOpenEntity = onOpenEntity,
                        onPlay = onPlay,
                    )
                }
                if (pageCount > 1) {
                    PodcastPager(
                        currentPage = safePage,
                        pageCount = pageCount,
                        onPageChange = { currentPage = it },
                    )
                }
            }
        }
    }
}

@Composable
private fun PodcastEpisodeCard(
    podcast: PodcastDetailPodcast,
    episode: PodcastDetailEpisode,
    onOpenEntity: (AppRoute) -> Unit,
    onPlay: (PodcastPlaybackItem) -> Unit,
) {
    val context = LocalContext.current
    val playbackItem = episode.playbackItem(podcast)
    val action = { playbackItem?.let(onPlay) ?: context.openUrl(episode.episodeUrl) }
    val guests = episode.nonHostAppearances(podcast)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(LaughTrackColors.SurfaceMuted)
            .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(16.dp))
            .clickable(onClick = action)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Box {
                RemoteImage(
                    url = podcast.imageUrl,
                    contentDescription = podcast.title,
                    modifier = Modifier.size(56.dp).clip(RoundedCornerShape(10.dp)),
                    fallback = RemoteImageFallback.Podcast,
                )
                Surface(
                    shape = CircleShape,
                    color = LaughTrackColors.SurfaceElevated,
                    modifier = Modifier.size(22.dp).align(Alignment.BottomEnd),
                ) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Icon(
                            if (playbackItem != null) {
                                Icons.Filled.PlayArrow
                            } else {
                                Icons.AutoMirrored.Filled.OpenInNew
                            },
                            contentDescription = if (playbackItem != null) "Play episode" else "Open episode",
                            tint = LaughTrackColors.AccentStrong,
                            modifier = Modifier.size(16.dp),
                        )
                    }
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    episode.title,
                    style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold),
                    color = LaughTrackColors.Foreground,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    podcastEpisodeMetadata(episode),
                    style = MaterialTheme.typography.bodySmall,
                    color = LaughTrackColors.ForegroundMuted,
                    maxLines = 1,
                )
            }
        }
        if (guests.isNotEmpty()) {
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                guests.forEach { guest ->
                    Column(
                        Modifier
                            .width(64.dp)
                            .clickable { onOpenEntity(AppRoute.ComedianDetail(guest.id)) },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        RemoteImage(
                            url = guest.imageUrl,
                            contentDescription = guest.name,
                            modifier = Modifier.size(44.dp).clip(CircleShape),
                            fallback = RemoteImageFallback.Person,
                        )
                        Text(
                            guest.name,
                            style = MaterialTheme.typography.labelSmall,
                            color = LaughTrackColors.Foreground,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PodcastPager(
    currentPage: Int,
    pageCount: Int,
    onPageChange: (Int) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TextButton(onClick = { onPageChange(currentPage - 1) }, enabled = currentPage > 0) {
            Text("‹ Previous")
        }
        Text(
            "Page ${currentPage + 1} of $pageCount",
            style = MaterialTheme.typography.labelMedium,
            color = LaughTrackColors.ForegroundMuted,
        )
        TextButton(onClick = { onPageChange(currentPage + 1) }, enabled = currentPage < pageCount - 1) {
            Text("Next ›")
        }
    }
}

@Composable
private fun PodcastFrequentGuestsSection(
    guests: List<PodcastDetailEpisodeAppearance>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (guests.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PodcastSectionHeader(eyebrow = "Regulars", title = "Frequent guests")
        guests.forEach { guest ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(LaughTrackColors.SurfaceElevated)
                    .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(16.dp))
                    .clickable { onOpenEntity(AppRoute.ComedianDetail(guest.id)) }
                    .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    url = guest.imageUrl,
                    contentDescription = guest.name,
                    modifier = Modifier.size(44.dp).clip(CircleShape),
                    fallback = RemoteImageFallback.Person,
                )
                Text(
                    guest.name,
                    style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold),
                    color = LaughTrackColors.Foreground,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text("›", color = LaughTrackColors.ForegroundMuted, style = MaterialTheme.typography.headlineSmall)
            }
        }
    }
}

@Composable
private fun PodcastSectionHeader(
    eyebrow: String,
    title: String,
) {
    Column(
        Modifier.padding(top = 16.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(
            eyebrow.uppercase(Locale.US),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = LaughTrackColors.AccentStrong,
        )
        Text(
            title,
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
            color = LaughTrackColors.Foreground,
        )
    }
}

@Composable
private fun PodcastEmptyCard(
    title: String,
    message: String,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(LaughTrackColors.SurfaceMuted)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, fontWeight = FontWeight.SemiBold, color = LaughTrackColors.Foreground)
        Text(message, style = MaterialTheme.typography.bodySmall, color = LaughTrackColors.ForegroundMuted)
    }
}

internal fun frequentPodcastGuests(
    response: PodcastDetailResponse,
    cap: Int = 3,
): List<PodcastDetailEpisodeAppearance> {
    val hostIds = response.podcast.hosts.mapTo(mutableSetOf()) { it.id }
    val hostUuids = response.podcast.hosts.mapTo(mutableSetOf()) { it.uuid }
    val episodeIdsByGuest = mutableMapOf<Int, MutableSet<Int>>()
    val firstAppearance = mutableMapOf<Int, PodcastDetailEpisodeAppearance>()

    response.episodes.forEach { episode ->
        episode.appearances.forEach { appearance ->
            if (appearance.id !in hostIds && appearance.uuid !in hostUuids) {
                episodeIdsByGuest.getOrPut(appearance.id) { mutableSetOf() }.add(episode.id)
                firstAppearance.putIfAbsent(appearance.id, appearance)
            }
        }
    }

    return episodeIdsByGuest
        .filterValues { it.size >= 2 }
        .keys
        .mapNotNull(firstAppearance::get)
        .take(cap)
}

internal fun podcastEpisodeMetadata(episode: PodcastDetailEpisode): String {
    val date = formatPodcastReleaseDate(episode.releaseDate)
    val duration = formatPodcastDuration(episode.durationSeconds)
    return listOfNotNull(date, duration).joinToString(" • ").ifBlank { "Episode" }
}

private fun formatPodcastReleaseDate(raw: String?): String? {
    val value = raw?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    val date =
        runCatching { LocalDate.parse(value) }.getOrNull()
            ?: runCatching { OffsetDateTime.parse(value).toLocalDate() }.getOrNull()
            ?: return null
    return date.format(DateTimeFormatter.ofPattern("MMM d, yyyy", Locale.US))
}

private fun formatPodcastDuration(seconds: Int?): String? {
    if (seconds == null || seconds < 60) return null
    val totalMinutes = seconds / 60
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return when {
        hours > 0 && minutes > 0 -> "$hours hr $minutes min"
        hours > 0 -> "$hours hr"
        else -> "$minutes min"
    }
}

private fun PodcastDetailEpisode.isPlayableOrOpenable(): Boolean =
    !audioUrl.isNullOrBlank() || !episodeUrl.isNullOrBlank()

private fun PodcastDetailEpisode.nonHostAppearances(
    podcast: PodcastDetailPodcast,
): List<PodcastDetailEpisodeAppearance> {
    val hostIds = podcast.hosts.mapTo(mutableSetOf()) { it.id }
    val hostUuids = podcast.hosts.mapTo(mutableSetOf()) { it.uuid }
    return appearances.filter { it.id !in hostIds && it.uuid !in hostUuids }
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
