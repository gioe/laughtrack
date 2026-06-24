package app.laughtrack.android.core.playback

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.PlaybackParameters
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PodcastPlaybackController @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val _state = MutableStateFlow(PodcastPlaybackState())
    val state: StateFlow<PodcastPlaybackState> = _state.asStateFlow()

    val player: ExoPlayer = ExoPlayer.Builder(context).build()
    val mediaSession: MediaSession = MediaSession.Builder(context, player).build()

    init {
        player.addListener(
            object : Player.Listener {
                override fun onPlaybackStateChanged(playbackState: Int) {
                    publishState()
                }

                override fun onIsPlayingChanged(isPlaying: Boolean) {
                    publishState()
                }

                override fun onPlaybackParametersChanged(playbackParameters: PlaybackParameters) {
                    publishState()
                }
            },
        )
        scope.launch {
            while (true) {
                publishState()
                delay(500)
            }
        }
    }

    fun play(item: PodcastPlaybackItem) {
        startPlaybackService()
        val mediaItem = MediaItem.Builder()
            .setUri(item.audioUrl)
            .setMediaId(item.episodeId.toString())
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(item.episodeTitle)
                    .setArtist(item.podcastTitle)
                    .setArtworkUri(item.artworkUrl?.let(Uri::parse))
                    .build(),
            )
            .build()

        _state.value = _state.value.copy(currentItem = item, positionMs = 0L)
        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()
        publishState()
    }

    fun togglePlayPause() {
        if (player.isPlaying) {
            player.pause()
        } else {
            player.play()
        }
        publishState()
    }

    fun seekTo(positionMs: Long) {
        player.seekTo(positionMs.coerceAtLeast(0L))
        publishState()
    }

    fun setPlaybackRate(rate: Float) {
        player.setPlaybackSpeed(rate)
        publishState()
    }

    fun stop() {
        player.stop()
        context.stopService(Intent(context, PodcastPlaybackService::class.java))
        _state.value = PodcastPlaybackState()
    }

    private fun startPlaybackService() {
        val intent = Intent(context, PodcastPlaybackService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent)
        } else {
            context.startService(intent)
        }
    }

    private fun publishState() {
        val current = _state.value
        _state.value = current.copy(
            isPlaying = player.isPlaying,
            positionMs = player.currentPosition.coerceAtLeast(0L),
            durationMs = player.duration
                .takeIf { it != C.TIME_UNSET }
                ?.coerceAtLeast(0L)
                ?: current.durationMs,
            playbackRate = player.playbackParameters.speed,
            isBuffering = player.playbackState == Player.STATE_BUFFERING,
        )
    }
}
