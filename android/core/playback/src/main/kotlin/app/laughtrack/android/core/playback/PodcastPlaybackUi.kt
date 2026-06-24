package app.laughtrack.android.core.playback

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.components.RemoteImage

@Composable
fun PodcastMiniPlayer(
    playbackController: PodcastPlaybackController,
    onExpand: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by playbackController.state.collectAsState()
    val item = state.currentItem ?: return

    Card(
        modifier = modifier
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
                TextButton(onClick = { playbackController.togglePlayPause() }) {
                    Text(if (state.isPlaying) "Pause" else "Play")
                }
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
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        RemoteImage(
            url = item.artworkUrl,
            contentDescription = item.podcastTitle,
            contentScale = ContentScale.Crop,
            modifier = Modifier
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

        TextButton(onClick = { playbackController.togglePlayPause() }) {
            Text(if (state.isPlaying) "Pause" else "Play")
        }

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

private fun PodcastPlaybackState.progressFraction(): Float {
    if (durationMs <= 0L) return 0f
    return (positionMs.toFloat() / durationMs.toFloat()).coerceIn(0f, 1f)
}

private fun PodcastPlaybackState.sliderDuration(): Long =
    durationMs.takeIf { it > 0L } ?: 1L

private fun Float.cleanRate(): String =
    if (this % 1f == 0f) toInt().toString() else toString()

private fun formatTime(ms: Long): String {
    val totalSeconds = (ms / 1_000).coerceAtLeast(0L)
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "$minutes:${seconds.toString().padStart(2, '0')}"
}
