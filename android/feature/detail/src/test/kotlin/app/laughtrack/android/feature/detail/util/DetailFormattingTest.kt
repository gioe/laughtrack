package app.laughtrack.android.feature.detail.util

import app.laughtrack.android.core.network.generated.model.Ticket
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal
import java.time.ZoneOffset
import java.time.ZonedDateTime

class DetailFormattingTest {
    private val now = ZonedDateTime.of(2026, 6, 24, 10, 0, 0, 0, ZoneOffset.UTC)

    @Test
    fun `ticket outbound url carries params and url-encodes the destination`() {
        val url =
            buildTicketOutboundUrl(
                apiBaseUrl = "https://www.laugh-track.com/api/v1",
                showId = 10,
                clubId = 5,
                destinationUrl = "https://tickets.example.com/buy?seat=A1",
            )
        assertEquals(
            "https://www.laugh-track.com/api/v1/tickets/out?showId=10&clubId=5&surface=show_detail&url=" +
                "https%3A%2F%2Ftickets.example.com%2Fbuy%3Fseat%3DA1",
            url,
        )
    }

    @Test
    fun `ticket outbound url trims a trailing slash on the base`() {
        val url = buildTicketOutboundUrl("https://host/api/v1/", 1, 2, "https://x.test")
        assertTrue(url!!.startsWith("https://host/api/v1/tickets/out?"))
    }

    @Test
    fun `ticket outbound url is null without a destination`() {
        assertNull(buildTicketOutboundUrl("https://host/api/v1", 1, 2, null))
        assertNull(buildTicketOutboundUrl("https://host/api/v1", 1, 2, "   "))
    }

    @Test
    fun `parses iso timestamps with and without offset`() {
        assertEquals(2026, parseShowDateTime("2026-06-27T20:00:00-04:00")?.year)
        assertEquals(2026, parseShowDateTime("2026-06-27T20:00:00Z")?.year)
        assertNull(parseShowDateTime(""))
        assertNull(parseShowDateTime("not-a-date"))
    }

    @Test
    fun `show timestamp is rendered in its venue timezone`() {
        val parsed = parseShowDateTime("2026-07-13T23:00:00Z", "America/New_York")

        assertEquals("America/New_York", parsed?.zone?.id)
        assertEquals(19, parsed?.hour)
        assertTrue(formatShowDateTime("2026-07-13T23:00:00Z", "America/New_York").contains("7:00 PM"))
    }

    @Test
    fun `countdown reports days, hours, minutes, and past`() {
        assertEquals("In 3 days", formatCountdown("2026-06-27T10:00:00Z", now))
        assertEquals("In 1 day", formatCountdown("2026-06-25T10:00:00Z", now))
        assertEquals("In 5 hours", formatCountdown("2026-06-24T15:00:00Z", now))
        assertEquals("In 1 hour", formatCountdown("2026-06-24T11:00:00Z", now))
        assertEquals("In 30 minutes", formatCountdown("2026-06-24T10:30:00Z", now))
        assertEquals("Past show", formatCountdown("2026-06-23T10:00:00Z", now))
        assertNull(formatCountdown("garbage", now))
    }

    @Test
    fun `episode duration formats hours and minutes`() {
        assertEquals("1h 2m", formatEpisodeDuration(3720))
        assertEquals("47m", formatEpisodeDuration(2820))
        assertNull(formatEpisodeDuration(null))
        assertNull(formatEpisodeDuration(0))
    }

    @Test
    fun `release date formats a plain date and tolerates junk`() {
        assertTrue(formatReleaseDate("2026-06-14")!!.contains("2026"))
        assertNull(formatReleaseDate(null))
        assertNull(formatReleaseDate(""))
        assertEquals("whenever", formatReleaseDate("whenever"))
    }

    @Test
    fun `home city joins city with region, preferring state then country`() {
        assertEquals("Austin, TX", formatHomeCity("Austin", "TX", "USA"))
        assertEquals("Toronto, Canada", formatHomeCity("Toronto", null, "Canada"))
        assertEquals("Brooklyn", formatHomeCity("Brooklyn", "  ", null))
    }

    @Test
    fun `home city is null when the city is blank or absent`() {
        assertNull(formatHomeCity(null, "TX", "USA"))
        assertNull(formatHomeCity("   ", "TX", "USA"))
    }

    @Test
    fun `home club name trims and nulls blanks`() {
        assertEquals("The Stand", formatHomeClubName("  The Stand  "))
        assertNull(formatHomeClubName(null))
        assertNull(formatHomeClubName("   "))
    }

    @Test
    fun `ticket price label prefers sold out, then cheapest available price`() {
        assertEquals("Sold out", formatTicketPriceLabel(tickets = null, soldOut = true))
        assertEquals(
            "$20.00",
            formatTicketPriceLabel(
                tickets =
                    listOf(
                        Ticket(price = BigDecimal("25")),
                        Ticket(price = BigDecimal("20")),
                        Ticket(price = BigDecimal("10"), soldOut = true),
                    ),
                soldOut = false,
            ),
        )
        assertEquals(
            "Free",
            formatTicketPriceLabel(tickets = listOf(Ticket(price = BigDecimal.ZERO)), soldOut = null),
        )
    }

    @Test
    fun `ticket price label is null without priced tickets`() {
        assertNull(formatTicketPriceLabel(tickets = null, soldOut = null))
        assertNull(formatTicketPriceLabel(tickets = emptyList(), soldOut = false))
        assertNull(formatTicketPriceLabel(tickets = listOf(Ticket(price = null)), soldOut = null))
    }

    @Test
    fun `ticket price label reports sold out when every ticket is sold out`() {
        assertEquals(
            "Sold out",
            formatTicketPriceLabel(
                tickets = listOf(Ticket(price = BigDecimal("20"), soldOut = true), Ticket(soldOut = true)),
                soldOut = null,
            ),
        )
    }

    @Test
    fun `show row title prefers name and dedupes the club from the subtitle`() {
        assertEquals(
            "Late Show" to "The Stand · New York",
            showRowTitleSubtitle("Late Show", "The Stand", "New York"),
        )
        assertEquals(
            "The Stand" to "New York",
            showRowTitleSubtitle(null, "The Stand", "New York"),
        )
        assertEquals(
            "THE STAND" to "New York",
            showRowTitleSubtitle("THE STAND", "The Stand", "New York"),
        )
        assertEquals("Show" to null, showRowTitleSubtitle(null, null, null))
    }
}
