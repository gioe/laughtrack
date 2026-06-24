package app.laughtrack.android.core.playback

data class PodcastPlaybackItem(
    val episodeId: Int,
    val podcastId: Int,
    val podcastTitle: String,
    val episodeTitle: String,
    val audioUrl: String,
    val artworkUrl: String?,
)
