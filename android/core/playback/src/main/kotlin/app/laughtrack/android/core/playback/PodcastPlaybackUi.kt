package app.laughtrack.android.core.playback

import android.os.SystemClock
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Forward30
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import kotlinx.coroutines.delay

internal enum class NowPlayingLayoutMode {
    Compact,
    Expanded,
}

internal data class NowPlayingLayoutSpec(
    val mode: NowPlayingLayoutMode,
    val artworkSize: Dp,
    val contentMaxWidth: Dp,
)

internal fun nowPlayingLayoutSpec(availableWidth: Dp): NowPlayingLayoutSpec {
    val expanded = availableWidth >= EXPANDED_PLAYER_BREAKPOINT
    return if (expanded) {
        NowPlayingLayoutSpec(
            mode = NowPlayingLayoutMode.Expanded,
            artworkSize = (availableWidth * EXPANDED_ARTWORK_WIDTH_RATIO).coerceIn(360.dp, 480.dp),
            contentMaxWidth = 620.dp,
        )
    } else {
        NowPlayingLayoutSpec(
            mode = NowPlayingLayoutMode.Compact,
            artworkSize = (availableWidth - 48.dp).coerceIn(220.dp, 340.dp),
            contentMaxWidth = 520.dp,
        )
    }
}

internal data class PodcastPlaybackUiModel(
    val item: PodcastPlaybackItem?,
    val isPlaying: Boolean,
    val positionMs: Long,
    val durationMs: Long,
    val playbackRate: Float,
    val sleepTimerEndsAtElapsedMs: Long?,
) {
    fun progressFraction(): Float {
        if (durationMs <= 0L) return 0f
        return (positionMs.toFloat() / durationMs.toFloat()).coerceIn(0f, 1f)
    }

    fun sliderDuration(): Long = durationMs.takeIf { it > 0L } ?: 1L
}

internal fun PodcastPlaybackState.toPlaybackUiModel(): PodcastPlaybackUiModel =
    PodcastPlaybackUiModel(
        item = currentItem,
        isPlaying = isPlaying,
        positionMs = positionMs,
        durationMs = durationMs,
        playbackRate = playbackRate,
        sleepTimerEndsAtElapsedMs = sleepTimerEndsAtElapsedMs,
    )

internal data class PlaybackControlLabels(
    val playPause: String,
    val skipBack: String = "Skip back 15 seconds",
    val skipForward: String = "Skip forward 30 seconds",
    val sleepTimer: String = "Sleep timer",
    val playbackSpeed: String = "Playback speed",
)

internal fun playbackControlLabels(isPlaying: Boolean): PlaybackControlLabels =
    PlaybackControlLabels(playPause = if (isPlaying) "Pause" else "Play")

@Composable
fun PodcastMiniPlayer(
    playbackController: PodcastPlaybackController,
    onExpand: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by playbackController.state.collectAsState()
    val ui = state.toPlaybackUiModel()
    val item = ui.item ?: return

    Card(
        modifier =
            modifier
                .fillMaxWidth()
                .clickable(onClick = onExpand),
    ) {
        Column {
            LinearProgressIndicator(
                progress = { ui.progressFraction() },
                modifier = Modifier.fillMaxWidth(),
            )
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                RemoteImage(
                    url = item.artworkUrl,
                    fallback = RemoteImageFallback.Podcast,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.size(44.dp).clip(RoundedCornerShape(6.dp)),
                )
                Column(Modifier.weight(1f)) {
                    Text(
                        item.episodeTitle,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        item.podcastTitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                MiniTransportButton(
                    icon = Icons.Filled.Replay,
                    contentDescription = playbackControlLabels(ui.isPlaying).skipBack,
                    onClick = playbackController::skipBack,
                )
                MiniTransportButton(
                    icon = if (ui.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                    contentDescription = playbackControlLabels(ui.isPlaying).playPause,
                    emphasized = true,
                    onClick = playbackController::togglePlayPause,
                )
                MiniTransportButton(
                    icon = Icons.Filled.Forward30,
                    contentDescription = playbackControlLabels(ui.isPlaying).skipForward,
                    onClick = playbackController::skipForward,
                )
            }
        }
    }
}

@Composable
private fun MiniTransportButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    emphasized: Boolean = false,
) {
    IconButton(
        onClick = onClick,
        modifier =
            Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(
                    if (emphasized) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.surfaceContainerHighest
                    },
                ),
    ) {
        Icon(icon, contentDescription = contentDescription, modifier = Modifier.size(21.dp))
    }
}

@Composable
fun NowPlayingScreen(
    playbackController: PodcastPlaybackController,
    modifier: Modifier = Modifier,
) {
    val state by playbackController.state.collectAsState()
    val ui = state.toPlaybackUiModel()
    val item = ui.item

    if (item == null) {
        Column(
            modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Nothing playing", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    BoxWithConstraints(modifier.fillMaxSize()) {
        val spec = nowPlayingLayoutSpec(maxWidth)
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            if (spec.mode == NowPlayingLayoutMode.Compact) {
                CompactNowPlayingContent(
                    ui = ui,
                    playbackController = playbackController,
                    spec = spec,
                )
            } else {
                ExpandedNowPlayingContent(
                    ui = ui,
                    playbackController = playbackController,
                    spec = spec,
                )
            }
        }
    }
}

@Composable
private fun CompactNowPlayingContent(
    ui: PodcastPlaybackUiModel,
    playbackController: PodcastPlaybackController,
    spec: NowPlayingLayoutSpec,
) {
    Column(
        modifier =
            Modifier
                .widthIn(max = spec.contentMaxWidth)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        PlayerArtwork(ui = ui, artworkSize = spec.artworkSize)
        PlayerDetails(ui)
        PlayerProgress(ui = ui, playbackController = playbackController)
        PlayerControls(ui = ui, playbackController = playbackController)
    }
}

@Composable
private fun ExpandedNowPlayingContent(
    ui: PodcastPlaybackUiModel,
    playbackController: PodcastPlaybackController,
    spec: NowPlayingLayoutSpec,
) {
    Column(
        modifier =
            Modifier
                .widthIn(max = spec.contentMaxWidth)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 32.dp, vertical = 28.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        PlayerArtwork(ui = ui, artworkSize = spec.artworkSize)
        Column(
            modifier = Modifier.widthIn(max = 520.dp).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            PlayerDetails(ui)
            PlayerProgress(ui = ui, playbackController = playbackController)
            PlayerControls(ui = ui, playbackController = playbackController)
        }
    }
}

@Composable
private fun PlayerArtwork(
    ui: PodcastPlaybackUiModel,
    artworkSize: Dp,
) {
    val item = requireNotNull(ui.item)
    RemoteImage(
        url = item.artworkUrl,
        fallback = RemoteImageFallback.Podcast,
        contentDescription = item.podcastTitle,
        contentScale = ContentScale.Crop,
        modifier =
            Modifier
                .size(artworkSize)
                .clip(RoundedCornerShape(18.dp)),
    )
}

@Composable
private fun PlayerDetails(ui: PodcastPlaybackUiModel) {
    val item = requireNotNull(ui.item)
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            item.episodeTitle,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onBackground,
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            item.podcastTitle,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun PlayerProgress(
    ui: PodcastPlaybackUiModel,
    playbackController: PodcastPlaybackController,
) {
    Column(Modifier.fillMaxWidth()) {
        Slider(
            value = ui.positionMs.toFloat().coerceIn(0f, ui.sliderDuration().toFloat()),
            onValueChange = { playbackController.seekTo(it.toLong()) },
            valueRange = 0f..ui.sliderDuration().toFloat(),
        )
        Row(Modifier.fillMaxWidth()) {
            Text(
                formatTime(ui.positionMs),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.weight(1f))
            Text(
                formatTime(ui.durationMs),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun PlayerControls(
    ui: PodcastPlaybackUiModel,
    playbackController: PodcastPlaybackController,
) {
    val labels = playbackControlLabels(ui.isPlaying)
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(24.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SkipControl(
                icon = Icons.Filled.Replay,
                contentDescription = labels.skipBack,
                intervalLabel = "15 sec",
                onClick = playbackController::skipBack,
            )
            IconButton(
                onClick = playbackController::togglePlayPause,
                modifier =
                    Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
            ) {
                Icon(
                    imageVector = if (ui.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                    contentDescription = labels.playPause,
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(34.dp),
                )
            }
            SkipControl(
                icon = Icons.Filled.Forward30,
                contentDescription = labels.skipForward,
                intervalLabel = "30 sec",
                onClick = playbackController::skipForward,
            )
        }
        SleepTimerMenu(
            endsAtElapsedMs = ui.sleepTimerEndsAtElapsedMs,
            playbackController = playbackController,
        )
        PlaybackSpeedControls(ui = ui, playbackController = playbackController)
    }
}

@Composable
private fun SkipControl(
    icon: ImageVector,
    contentDescription: String,
    intervalLabel: String,
    onClick: () -> Unit,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        IconButton(
            onClick = onClick,
            modifier =
                Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceContainerHighest),
        ) {
            Icon(
                icon,
                contentDescription = contentDescription,
                tint = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.size(26.dp),
            )
        }
        Text(
            intervalLabel,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun PlaybackSpeedControls(
    ui: PodcastPlaybackUiModel,
    playbackController: PodcastPlaybackController,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Filled.Speed,
                contentDescription = playbackControlLabels(ui.isPlaying).playbackSpeed,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Playback speed",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
        ) {
            PLAYBACK_RATES.forEach { rate ->
                AssistChip(
                    onClick = { playbackController.setPlaybackRate(rate) },
                    label = { Text("${rate.cleanRate()}x") },
                    enabled = ui.playbackRate != rate,
                )
            }
        }
    }
}

/** Sleep-timer trigger: shows a live countdown when armed, opens an interval menu. */
@Composable
private fun SleepTimerMenu(
    endsAtElapsedMs: Long?,
    playbackController: PodcastPlaybackController,
) {
    var expanded by remember { mutableStateOf(false) }
    var nowElapsedMs by remember { mutableStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(endsAtElapsedMs) {
        while (endsAtElapsedMs != null) {
            nowElapsedMs = SystemClock.elapsedRealtime()
            delay(1_000)
        }
    }
    Box {
        TextButton(onClick = { expanded = true }) {
            Icon(Icons.Filled.Timer, contentDescription = "Sleep timer")
            Spacer(Modifier.size(6.dp))
            Text(sleepTimerLabel(endsAtElapsedMs, nowElapsedMs))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            SLEEP_INTERVALS.forEach { (label, durationMs) ->
                DropdownMenuItem(
                    text = { Text(label) },
                    onClick = {
                        expanded = false
                        playbackController.setSleepTimer(durationMs)
                    },
                )
            }
        }
    }
}

private val PLAYBACK_RATES = listOf(0.8f, 1f, 1.25f, 1.5f, 2f)

/** Sleep-timer interval options, mirroring iOS NowPlayingView.sleepIntervals. */
private val SLEEP_INTERVALS: List<Pair<String, Long?>> =
    listOf(
        "Off" to null,
        "5 min" to 5 * 60_000L,
        "10 min" to 10 * 60_000L,
        "15 min" to 15 * 60_000L,
        "30 min" to 30 * 60_000L,
        "45 min" to 45 * 60_000L,
        "1 hour" to 60 * 60_000L,
    )

/**
 * Label for the sleep-timer button: "Sleep" when disarmed, or "Sleep · m:ss" with
 * the remaining time when a timer is running. Pure so the countdown is testable.
 */
internal fun sleepTimerLabel(
    endsAtElapsedMs: Long?,
    nowElapsedMs: Long,
): String {
    if (endsAtElapsedMs == null) return "Sleep"
    val remainingMs = (endsAtElapsedMs - nowElapsedMs).coerceAtLeast(0L)
    return "Sleep · ${formatTime(remainingMs)}"
}

private fun Float.cleanRate(): String = if (this % 1f == 0f) toInt().toString() else toString()

private fun formatTime(ms: Long): String {
    val totalSeconds = (ms / 1_000).coerceAtLeast(0L)
    val hours = totalSeconds / 3600
    val minutes = (totalSeconds % 3600) / 60
    val seconds = totalSeconds % 60
    return if (hours > 0) {
        "$hours:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}"
    } else {
        "$minutes:${seconds.toString().padStart(2, '0')}"
    }
}

private val EXPANDED_PLAYER_BREAKPOINT = 600.dp
private const val EXPANDED_ARTWORK_WIDTH_RATIO = 0.60f
