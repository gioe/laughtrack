package app.laughtrack.android.feature.notifications

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.ZoneOffset
import java.time.ZonedDateTime

class RelativeTimeTest {

    private val now = ZonedDateTime.of(2026, 6, 24, 12, 0, 0, 0, ZoneOffset.UTC)

    @Test
    fun `formats minutes, hours, days, and weeks ago`() {
        assertEquals("5m", formatTimeAgo("2026-06-24T11:55:00Z", now))
        assertEquals("2h", formatTimeAgo("2026-06-24T10:00:00Z", now))
        assertEquals("3d", formatTimeAgo("2026-06-21T12:00:00Z", now))
        assertEquals("2w", formatTimeAgo("2026-06-10T12:00:00Z", now))
    }

    @Test
    fun `recent and future timestamps read as now`() {
        assertEquals("now", formatTimeAgo("2026-06-24T11:59:30Z", now))
        assertEquals("now", formatTimeAgo("2026-06-24T12:05:00Z", now))
    }

    @Test
    fun `parses an offset timestamp`() {
        assertEquals("1h", formatTimeAgo("2026-06-24T07:00:00-04:00", now))
    }

    @Test
    fun `null and unparseable inputs return null`() {
        assertNull(formatTimeAgo(null, now))
        assertNull(formatTimeAgo("", now))
        assertNull(formatTimeAgo("not-a-date", now))
    }
}
