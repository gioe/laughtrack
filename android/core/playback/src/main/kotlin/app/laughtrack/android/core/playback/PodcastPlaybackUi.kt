package app.laughtrack.android.core.playback

import android.os.SystemClock
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import kotlinx.coroutines.delay

@Composable
fun PodcastMiniPlayer(
    playbackController: PodcastPlaybackController,
    onExpand: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by playbackController.state.collectAsState()
    val item = state.currentItem ?: return

    Card(
        modifier =
            modifier
                .fillMaxWidth()
                .clickable(onClick = onExpand),
    ) {
        Column {
            LinearProgressIndicator(
                progress = { state.progressFraction() },
                modifier = Modifier.fillMaxWidth(),
            )
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                RemoteImage(
                    url = item.artworkUrl,
                    fallback = RemoteImageFallback.Podcast,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.size(48.dp),
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
                SleepTimerMenu(state = state, playbackController = playbackController)
                TextButton(onClick = { playbackController.skipBack() }) { Text("-15s") }
                TextButton(onClick = { playbackController.togglePlayPause() }) {
                    Text(if (state.isPlaying) "Pause" else "Play")
                }
                TextButton(onClick = { playbackController.skipForward() }) { Text("+30s") }
            }
        }
    }
}

@Composable
fun NowPlayingScreen(
    playbackController: PodcastPlaybackController,
    modifier: Modifier = Modifier,
) {
    val state by playbackController.state.collectAsState()
    val item = state.currentItem

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

    Column(
        modifier =
            modifier
                .fillMaxSize()
                .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        RemoteImage(
            url = item.artworkUrl,
            fallback = RemoteImageFallback.Podcast,
            contentDescription = item.podcastTitle,
            contentScale = ContentScale.Crop,
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(280.dp),
        )
        Text(
            item.episodeTitle,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            item.podcastTitle,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )

        Column(Modifier.fillMaxWidth()) {
            Slider(
                value = state.positionMs.toFloat(),
                onValueChange = { playbackController.seekTo(it.toLong()) },
                valueRange = 0f..state.sliderDuration().toFloat(),
            )
            Row(Modifier.fillMaxWidth()) {
                Text(formatTime(state.positionMs), style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.weight(1f))
                Text(formatTime(state.durationMs), style = MaterialTheme.typography.bodySmall)
            }
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = { playbackController.skipBack() }) { Text("-15s") }
            TextButton(onClick = { playbackController.togglePlayPause() }) {
                Text(if (state.isPlaying) "Pause" else "Play")
            }
            TextButton(onClick = { playbackController.skipForward() }) { Text("+30s") }
        }

        SleepTimerMenu(state = state, playbackController = playbackController)

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(0.8f, 1f, 1.25f, 1.5f, 2f).forEach { rate ->
                AssistChip(
                    onClick = { playbackController.setPlaybackRate(rate) },
                    label = { Text("${rate.cleanRate()}x") },
                    enabled = state.playbackRate != rate,
                )
            }
        }
    }
}

/** Sleep-timer trigger: shows a live countdown when armed, opens an interval menu. */
@Composable
private fun SleepTimerMenu(
    state: PodcastPlaybackState,
    playbackController: PodcastPlaybackController,
) {
    var expanded by remember { mutableStateOf(false) }
    // Re-read the clock once a second while a timer is armed so the countdown ticks
    // independently of playback (position polling would otherwise be the only
    // recomposition trigger, freezing the label while paused).
    var nowElapsedMs by remember { mutableStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(state.sleepTimerEndsAtElapsedMs) {
        while (state.sleepTimerEndsAtElapsedMs != null) {
            nowElapsedMs = SystemClock.elapsedRealtime()
            delay(1_000)
        }
    }
    Box {
        TextButton(onClick = { expanded = true }) {
            Text(sleepTimerLabel(state.sleepTimerEndsAtElapsedMs, nowElapsedMs))
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

private fun PodcastPlaybackState.progressFraction(): Float {
    if (durationMs <= 0L) return 0f
    return (positionMs.toFloat() / durationMs.toFloat()).coerceIn(0f, 1f)
}

private fun PodcastPlaybackState.sliderDuration(): Long = durationMs.takeIf { it > 0L } ?: 1L

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
