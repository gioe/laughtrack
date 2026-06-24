package app.laughtrack.android.core.playback

import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class PodcastPlaybackService : MediaSessionService() {
    @Inject
    lateinit var playbackController: PodcastPlaybackController

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? =
        playbackController.mediaSession
}
