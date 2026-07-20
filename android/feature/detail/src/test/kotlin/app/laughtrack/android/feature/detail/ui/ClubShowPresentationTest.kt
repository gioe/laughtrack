package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.Ticket
import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class ClubShowPresentationTest {
    @Test
    fun card_leads_with_the_most_established_comedian_and_orders_supporting_lineup() {
        val show =
            show(
                lineup =
                    listOf(
                        comedian(1, "Paula J. Leon", 10),
                        comedian(2, "Judah Friedlander", 100),
                        comedian(3, "Michael Brigante", 40),
                    ),
            )

        val headliner = clubShowHeadliner(show)
        val supporting = clubShowSupportingLineup(show, excluding = headliner)

        assertEquals("Judah Friedlander", headliner?.name)
        assertEquals(listOf("Michael Brigante", "Paula J. Leon"), supporting.map { it.name })
    }

    @Test
    fun card_resolves_aliases_to_their_parent_comedian() {
        val parent = comedian(9, "Parent Headliner", 100)
        val alias = comedian(10, "Stage Alias", 1, parent = parent)

        assertEquals(parent, clubShowHeadliner(show(lineup = listOf(alias))))
    }

    @Test
    fun standout_requires_one_unique_positive_popularity_score() {
        val ordinary = show(id = 1, popularity = "5")
        val standout = show(id = 2, popularity = "12")

        assertEquals(2, clubShowStandoutId(listOf(ordinary, standout)))
        assertEquals(null, clubShowStandoutId(listOf(standout, show(id = 3, popularity = "12"))))
    }

    @Test
    fun venue_line_and_row_price_match_ios_compact_ticket_presentation() {
        val show =
            show(
                clubLocation = ClubLocation(city = "New York", state = "NY"),
                tickets = listOf(Ticket(price = BigDecimal("25.00"))),
            )

        assertEquals("New York Comedy Club Midtown • New York, NY", clubShowVenueLine(club(), show))
        assertEquals("$25", clubShowTicketLabel(show))
    }

    private fun show(
        id: Int = 1,
        lineup: List<ComedianLineup> = emptyList(),
        popularity: String? = null,
        clubLocation: ClubLocation? = null,
        tickets: List<Ticket>? = null,
    ) = Show(
        id = id,
        clubId = 2,
        date = "2026-07-13T23:00:00Z",
        imageUrl = "",
        lineup = lineup,
        popularityScore = popularity?.let(::BigDecimal),
        clubCity = clubLocation?.city,
        clubState = clubLocation?.state,
        tickets = tickets,
    )

    private fun club() =
        ClubDetail(
            id = 2,
            name = "New York Comedy Club Midtown",
            imageUrl = "",
            heroImageUrl = "",
            website = "",
            address = "",
            zipCode = "",
            phoneNumber = "",
        )

    private fun comedian(
        id: Int,
        name: String,
        showCount: Int,
        parent: ComedianLineup? = null,
    ) = ComedianLineup(
        id = id,
        uuid = "uuid-$id",
        name = name,
        imageUrl = "https://example.com/$id.jpg",
        showCount = showCount,
        parentComedian = parent,
    )

    private data class ClubLocation(
        val city: String,
        val state: String,
    )
}
