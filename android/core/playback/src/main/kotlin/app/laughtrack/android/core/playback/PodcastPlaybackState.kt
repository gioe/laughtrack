package app.laughtrack.android.core.playback

data class PodcastPlaybackState(
    val currentItem: PodcastPlaybackItem? = null,
    val isPlaying: Boolean = false,
    val positionMs: Long = 0L,
    val durationMs: Long = 0L,
    val playbackRate: Float = 1f,
    val isBuffering: Boolean = false,
    /**
     * When a sleep timer is armed, the SystemClock.elapsedRealtime() deadline at
     * which playback fades out and pauses; null when no timer is set. Held as an
     * elapsed-realtime instant so the UI can render a live countdown.
     */
    val sleepTimerEndsAtElapsedMs: Long? = null,
) {
    val hasItem: Boolean
        get() = currentItem != null

    val isSleepTimerActive: Boolean
        get() = sleepTimerEndsAtElapsedMs != null
}
