import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Authenticated screenshot persona")
struct AuthenticatedScreenshotPersonaTests {
    @Test("fixture is deterministic, useful, and contains no credentials")
    func deterministicCredentialsFreeFixture() {
        let first = AuthenticatedScreenshotPersona.shared
        let second = AuthenticatedScreenshotPersona.shared

        #expect(first == second)
        #expect(first.user.displayName == "Jordan Rivera")
        #expect(first.user.zipCode == "10012")
        #expect(first.favoriteComedians.count >= 2)
        #expect(first.upcomingSavedShows.allSatisfy { $0.tickets?.count == 1 })
        let dateFormatter = ISO8601DateFormatter()
        let savedShowStory = first.upcomingSavedShows.map { show in
            let ticket = show.tickets?.first
            return SavedShowStory(
                title: ShowTitlePresentation.title(for: show),
                date: dateFormatter.string(from: show.date),
                club: show.clubName,
                city: show.clubCity,
                state: show.clubState,
                timezone: show.timezone,
                price: ticket?.price,
                soldOut: ticket?.soldOut,
                ticketType: ticket?._type
            )
        }
        #expect(savedShowStory == [
            .init("Atsuko Okatsuka: Full Grown Tour", "2026-08-22T00:00:00Z", "Town Hall", "New York"),
            .init("Josh Johnson and Friends", "2026-08-25T00:00:00Z", "The Bell House", "Brooklyn"),
            .init("Taylor Tomlinson Live", "2026-08-29T00:00:00Z", "The Comedy Cellar", "New York"),
            .init("Sam Jay: Testing Material", "2026-09-02T23:30:00Z", "Union Hall", "Brooklyn"),
            .init("Mike Birbiglia: Please Stop the Ride", "2026-09-06T00:00:00Z", "Beacon Theatre", "New York"),
            .init("Michelle Wolf and Friends", "2026-09-09T00:00:00Z", "Gotham Comedy Club", "New York"),
        ])
        #expect(first.upcomingSavedShows.map(\.imageUrl) == [
            "https://laughtrack.b-cdn.net/comedians/Atsuko%20Okatsuka.png",
            "https://laughtrack.b-cdn.net/comedians/Josh%20Johnson.png",
            "https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg",
            "https://laughtrack.b-cdn.net/comedians/Sam%20Jay.png",
            "https://laughtrack.b-cdn.net/comedian-images/246654/da23a0ff-061c-4a8b-82b8-e8b197615ad7/avatar.jpg",
            "",
        ])
        #expect(first.favoriteClubs == ["The Comedy Cellar"])
        #expect(first.favoritePodcasts == ["Good One: A Podcast About Jokes"])
        #expect(first.notifications.count == 2)
        #expect(first.notifications.filter(\.isUnread).count == 1)
        #expect(first.notifications.map(\.body) == [
            "The Comedy Cellar on Saturday at 8:00 PM",
            "The Comedy Cellar and The Bell House",
        ])
        #expect(first.notifications.allSatisfy { $0.sentAt != nil })
        #expect(first.user.avatarURL == nil)
        #expect(first.user.email.hasSuffix(".invalid"))
    }
}

private struct SavedShowStory: Equatable {
    let title: String
    let date: String
    let club: String?
    let city: String?
    let state: String?
    let timezone: String?
    let price: Double?
    let soldOut: Bool?
    let ticketType: String?

    init(
        _ title: String,
        _ date: String,
        _ club: String,
        _ city: String,
        state: String = "NY",
        timezone: String = "America/New_York",
        price: Double = 30,
        soldOut: Bool = false,
        ticketType: String = "General admission"
    ) {
        self.title = title
        self.date = date
        self.club = club
        self.city = city
        self.state = state
        self.timezone = timezone
        self.price = price
        self.soldOut = soldOut
        self.ticketType = ticketType
    }

    init(
        title: String,
        date: String,
        club: String?,
        city: String?,
        state: String?,
        timezone: String?,
        price: Double?,
        soldOut: Bool?,
        ticketType: String?
    ) {
        self.title = title
        self.date = date
        self.club = club
        self.city = city
        self.state = state
        self.timezone = timezone
        self.price = price
        self.soldOut = soldOut
        self.ticketType = ticketType
    }
}
