package app.laughtrack.android.core.playback

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.SystemClock
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
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PodcastPlaybackController
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        private val _state = MutableStateFlow(PodcastPlaybackState())
        val state: StateFlow<PodcastPlaybackState> = _state.asStateFlow()

        val player: ExoPlayer by lazy {
            ExoPlayer.Builder(context).build().also { exoPlayer ->
                exoPlayer.addListener(
                    object : Player.Listener {
                        override fun onPlaybackStateChanged(playbackState: Int) {
                            publishState()
                        }

                        override fun onIsPlayingChanged(isPlaying: Boolean) {
                            if (isPlaying) {
                                positionTicker.start()
                            } else {
                                positionTicker.stop(finalPublish = true)
                            }
                        }

                        override fun onPlaybackParametersChanged(playbackParameters: PlaybackParameters) {
                            publishState()
                        }
                    },
                )
            }
        }

        val mediaSession: MediaSession by lazy { MediaSession.Builder(context, player).build() }

        private val positionTicker = PlaybackPositionTicker(scope, ::publishState)

        // The armed sleep-timer coroutine (pre-fade delay -> volume fade -> pause);
        // cancelled and nulled whenever the timer is reset, a new episode starts,
        // or playback stops.
        private var sleepJob: Job? = null

        fun play(item: PodcastPlaybackItem) {
            // A new episode clears any sleep timer armed for the previous one.
            sleepJob?.cancel()
            sleepJob = null
            player.volume = 1f
            startPlaybackService()
            val mediaItem =
                MediaItem.Builder()
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

            _state.value = _state.value.copy(currentItem = item, positionMs = 0L, sleepTimerEndsAtElapsedMs = null)
            player.setMediaItem(mediaItem)
            player.prepare()
            player.play()
            positionTicker.start()
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

        /** Jump back [SKIP_BACK_MS] (15s), clamped to the start of the episode. */
        fun skipBack() = seekTo(skipTargetMs(player.currentPosition, -SKIP_BACK_MS, currentDurationMs()))

        /** Jump forward [SKIP_FORWARD_MS] (30s), clamped to the episode duration. */
        fun skipForward() = seekTo(skipTargetMs(player.currentPosition, SKIP_FORWARD_MS, currentDurationMs()))

        /**
         * Arm (or, with null, cancel) a sleep timer. After [durationMs] elapses the
         * volume fades out over the final [SLEEP_FADE_MS] and playback pauses —
         * mirrors iOS setSleepTimer. Resets volume to full on cancel or completion.
         */
        fun setSleepTimer(durationMs: Long?) {
            sleepJob?.cancel()
            sleepJob = null
            player.volume = 1f
            if (durationMs == null || durationMs <= 0L) {
                _state.value = _state.value.copy(sleepTimerEndsAtElapsedMs = null)
                return
            }
            _state.value = _state.value.copy(sleepTimerEndsAtElapsedMs = SystemClock.elapsedRealtime() + durationMs)
            sleepJob =
                scope.launch {
                    val fadeMs = minOf(durationMs, SLEEP_FADE_MS)
                    delay((durationMs - fadeMs).coerceAtLeast(0L))
                    // Linear volume fade over the final window, then pause.
                    for (step in 1..SLEEP_FADE_STEPS) {
                        player.volume = (1f - step.toFloat() / SLEEP_FADE_STEPS).coerceIn(0f, 1f)
                        delay(fadeMs / SLEEP_FADE_STEPS)
                    }
                    player.pause()
                    player.volume = 1f
                    _state.value = _state.value.copy(sleepTimerEndsAtElapsedMs = null)
                    publishState()
                }
        }

        fun stop() {
            sleepJob?.cancel()
            sleepJob = null
            player.volume = 1f
            player.stop()
            positionTicker.stop(finalPublish = true)
            context.stopService(Intent(context, PodcastPlaybackService::class.java))
            _state.value = PodcastPlaybackState()
        }

        private fun currentDurationMs(): Long = player.duration.takeIf { it != C.TIME_UNSET } ?: 0L

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
            _state.value =
                current.copy(
                    isPlaying = player.isPlaying,
                    positionMs = player.currentPosition.coerceAtLeast(0L),
                    durationMs =
                        player.duration
                            .takeIf { it != C.TIME_UNSET }
                            ?.coerceAtLeast(0L)
                            ?: current.durationMs,
                    playbackRate = player.playbackParameters.speed,
                    isBuffering = player.playbackState == Player.STATE_BUFFERING,
                )
        }

        companion object {
            const val SKIP_BACK_MS = 15_000L
            const val SKIP_FORWARD_MS = 30_000L
            private const val SLEEP_FADE_MS = 10_000L
            private const val SLEEP_FADE_STEPS = 20
        }
    }

internal class PlaybackPositionTicker(
    private val scope: CoroutineScope,
    private val publishState: () -> Unit,
) {
    private var job: Job? = null

    fun start() {
        if (job?.isActive == true) return
        job =
            scope.launch {
                while (isActive) {
                    publishState()
                    delay(POSITION_POLL_MS)
                }
            }
    }

    fun stop(finalPublish: Boolean) {
        job?.cancel()
        job = null
        if (finalPublish) publishState()
    }

    internal fun isRunningForTest(): Boolean = job?.isActive == true

    private companion object {
        const val POSITION_POLL_MS = 500L
    }
}

/**
 * The seek target after applying [deltaMs] to [currentMs], clamped to
 * `0..durationMs` (the upper bound is ignored when [durationMs] is unknown/0).
 * Pure so the skip math is unit-testable without a player.
 */
internal fun skipTargetMs(
    currentMs: Long,
    deltaMs: Long,
    durationMs: Long,
): Long {
    val target = (currentMs + deltaMs).coerceAtLeast(0L)
    return if (durationMs > 0L) target.coerceAtMost(durationMs) else target
}
