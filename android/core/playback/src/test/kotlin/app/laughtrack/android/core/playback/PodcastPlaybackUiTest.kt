package app.laughtrack.android.core.playback

import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PodcastPlaybackUiTest {
    @Test
    fun phone_widths_use_compact_layout() {
        assertEquals(NowPlayingLayoutMode.Compact, nowPlayingLayoutSpec(440.dp).mode)
        assertEquals(NowPlayingLayoutMode.Compact, nowPlayingLayoutSpec(599.dp).mode)
    }

    @Test
    fun tablet_widths_use_expanded_layout() {
        assertEquals(NowPlayingLayoutMode.Expanded, nowPlayingLayoutSpec(600.dp).mode)
        assertEquals(NowPlayingLayoutMode.Expanded, nowPlayingLayoutSpec(800.dp).mode)
    }

    @Test
    fun artwork_is_square_by_contract_and_capped_for_each_layout() {
        assertEquals(340.dp, nowPlayingLayoutSpec(440.dp).artworkSize)
        assertEquals(340.dp, nowPlayingLayoutSpec(599.dp).artworkSize)
        assertEquals(228.dp, nowPlayingLayoutSpec(600.dp).artworkSize)
        assertEquals(304.dp, nowPlayingLayoutSpec(800.dp).artworkSize)
        assertEquals(360.dp, nowPlayingLayoutSpec(1_200.dp).artworkSize)
    }

    @Test
    fun ui_model_preserves_episode_and_playback_continuity_fields() {
        val item =
            PodcastPlaybackItem(
                episodeId = 42,
                podcastId = 7,
                podcastTitle = "LaughTrack",
                episodeTitle = "Comedy Roundup",
                audioUrl = "https://example.test/episode.mp3",
                artworkUrl = "https://example.test/art.jpg",
            )
        val state =
            PodcastPlaybackState(
                currentItem = item,
                isPlaying = true,
                positionMs = 45_000L,
                durationMs = 180_000L,
                playbackRate = 1.25f,
                sleepTimerEndsAtElapsedMs = 999_000L,
            )

        val ui = state.toPlaybackUiModel()

        assertEquals(item, ui.item)
        assertEquals(true, ui.isPlaying)
        assertEquals(45_000L, ui.positionMs)
        assertEquals(180_000L, ui.durationMs)
        assertEquals(1.25f, ui.playbackRate)
        assertEquals(999_000L, ui.sleepTimerEndsAtElapsedMs)
        assertNull(PodcastPlaybackState().toPlaybackUiModel().item)
    }

    @Test
    fun progress_clamps_unknown_negative_and_overrun_positions() {
        assertEquals(0f, uiModel(positionMs = 10_000L, durationMs = 0L).progressFraction())
        assertEquals(0f, uiModel(positionMs = -1_000L, durationMs = 10_000L).progressFraction())
        assertEquals(0.5f, uiModel(positionMs = 5_000L, durationMs = 10_000L).progressFraction())
        assertEquals(1f, uiModel(positionMs = 15_000L, durationMs = 10_000L).progressFraction())
    }

    @Test
    fun transport_accessibility_labels_describe_current_action_and_intervals() {
        val paused = playbackControlLabels(isPlaying = false)
        val playing = playbackControlLabels(isPlaying = true)

        assertEquals("Play", paused.playPause)
        assertEquals("Pause", playing.playPause)
        assertEquals("Skip back 15 seconds", paused.skipBack)
        assertEquals("Skip forward 30 seconds", paused.skipForward)
        assertEquals("Sleep timer", paused.sleepTimer)
        assertEquals("Playback speed", paused.playbackSpeed)
    }

    private fun uiModel(
        positionMs: Long,
        durationMs: Long,
    ): PodcastPlaybackUiModel =
        PodcastPlaybackUiModel(
            item = null,
            isPlaying = false,
            positionMs = positionMs,
            durationMs = durationMs,
            playbackRate = 1f,
            sleepTimerEndsAtElapsedMs = null,
        )
}
