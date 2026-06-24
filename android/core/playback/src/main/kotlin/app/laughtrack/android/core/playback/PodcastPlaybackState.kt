package app.laughtrack.android.core.playback

data class PodcastPlaybackState(
    val currentItem: PodcastPlaybackItem? = null,
    val isPlaying: Boolean = false,
    val positionMs: Long = 0L,
    val durationMs: Long = 0L,
    val playbackRate: Float = 1f,
    val isBuffering: Boolean = false,
) {
    val hasItem: Boolean
        get() = currentItem != null
}
