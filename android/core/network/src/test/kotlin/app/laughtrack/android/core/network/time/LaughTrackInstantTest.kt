package app.laughtrack.android.core.network.time

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.Instant

/**
 * Locks the flexible-decode contract: the adapter must accept both fractional
 * and whole-second ISO-8601 (the two forms the API emits) plus numeric offsets,
 * mirroring the iOS transcoder.
 */
class LaughTrackInstantTest {
    @Test
    fun parses_whole_second_utc() {
        assertEquals(
            Instant.parse("2024-06-21T15:30:45Z"),
            LaughTrackInstant.parse("2024-06-21T15:30:45Z"),
        )
    }

    @Test
    fun parses_fractional_second_utc() {
        assertEquals(
            Instant.parse("2024-06-21T15:30:45.123Z"),
            LaughTrackInstant.parse("2024-06-21T15:30:45.123Z"),
        )
    }

    @Test
    fun parses_numeric_offset() {
        // 15:30:45 at UTC-07:00 is 22:30:45Z.
        assertEquals(
            Instant.parse("2024-06-21T22:30:45Z"),
            LaughTrackInstant.parse("2024-06-21T15:30:45-07:00"),
        )
    }

    @Test
    fun parseOrNull_returns_null_for_null_blank_or_garbage() {
        assertNull(LaughTrackInstant.parseOrNull(null))
        assertNull(LaughTrackInstant.parseOrNull(""))
        assertNull(LaughTrackInstant.parseOrNull("not-a-date"))
    }

    @Test
    fun format_round_trips_whole_second_utc() {
        val raw = "2024-06-21T15:30:45Z"
        assertEquals(raw, LaughTrackInstant.format(LaughTrackInstant.parse(raw)))
    }
}
