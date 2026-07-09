package app.laughtrack.android.core.ui.components

import org.junit.Assert.assertEquals
import org.junit.Test

class TicketStubTest {
    @Test
    fun date_parts_use_the_show_timezone() {
        val parts =
            ticketStubDateParts(
                isoDateTime = "2026-07-04T02:30:00Z",
                timezone = "America/Los_Angeles",
                fallbackTime = "",
            )

        assertEquals(TicketDateParts(weekday = "FRI", day = "3", month = "JUL", time = "7:30 PM"), parts)
    }

    @Test
    fun invalid_date_keeps_fallback_time() {
        val parts =
            ticketStubDateParts(
                isoDateTime = "not-a-date",
                timezone = "America/New_York",
                fallbackTime = "Soon",
            )

        assertEquals(TicketDateParts(weekday = "", day = "", month = "", time = "Soon"), parts)
    }
}
