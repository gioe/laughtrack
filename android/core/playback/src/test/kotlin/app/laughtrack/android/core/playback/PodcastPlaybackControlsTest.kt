package app.laughtrack.android.core.playback

import org.junit.Assert.assertEquals
import org.junit.Test

/** Covers the pure skip-target math and sleep-timer countdown label. */
class PodcastPlaybackControlsTest {
    @Test
    fun skip_back_15s_clamps_to_start() {
        assertEquals(0L, skipTargetMs(currentMs = 10_000L, deltaMs = -15_000L, durationMs = 600_000L))
        assertEquals(45_000L, skipTargetMs(currentMs = 60_000L, deltaMs = -15_000L, durationMs = 600_000L))
    }

    @Test
    fun skip_forward_30s_clamps_to_duration() {
        assertEquals(120_000L, skipTargetMs(currentMs = 90_000L, deltaMs = 30_000L, durationMs = 600_000L))
        // Near the end, forward is capped at the duration.
        assertEquals(600_000L, skipTargetMs(currentMs = 590_000L, deltaMs = 30_000L, durationMs = 600_000L))
    }

    @Test
    fun unknown_duration_does_not_cap_forward() {
        assertEquals(120_000L, skipTargetMs(currentMs = 90_000L, deltaMs = 30_000L, durationMs = 0L))
    }

    @Test
    fun sleep_label_reads_sleep_when_disarmed() {
        assertEquals("Sleep", sleepTimerLabel(endsAtElapsedMs = null, nowElapsedMs = 5_000L))
    }

    @Test
    fun sleep_label_counts_down_remaining_time() {
        // 90s remaining -> "Sleep · 1:30".
        assertEquals("Sleep · 1:30", sleepTimerLabel(endsAtElapsedMs = 100_000L, nowElapsedMs = 10_000L))
        // Past the deadline clamps to 0:00 rather than going negative.
        assertEquals("Sleep · 0:00", sleepTimerLabel(endsAtElapsedMs = 10_000L, nowElapsedMs = 20_000L))
    }

    @Test
    fun sleep_label_rolls_over_to_hours_for_the_one_hour_option() {
        // 1h remaining renders h:mm:ss, not "60:00".
        assertEquals("Sleep · 1:00:00", sleepTimerLabel(endsAtElapsedMs = 3_600_000L, nowElapsedMs = 0L))
    }
}
