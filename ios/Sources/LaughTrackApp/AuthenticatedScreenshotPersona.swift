import Foundation
import LaughTrackAPIClient
import LaughTrackCore

/// Credentials-free, immutable content used only by explicit screenshot launches.
/// Keeping this at the view boundary prevents capture runs from touching auth or
/// mutable production APIs while still rendering the real authenticated pages.
/// Saved-show portraits use direct production CDN URLs so the Favorites capture
/// exercises real comedian artwork while retaining one missing-art fallback.
struct AuthenticatedScreenshotPersona: Equatable {
    static let launchEnvironmentKey = "UITEST_AUTHENTICATED_SCREENSHOT_PERSONA"

    static let shared = AuthenticatedScreenshotPersona()

    let user = AuthenticatedUser(
        userId: "screenshot-persona",
        displayName: "Jordan Rivera",
        email: "jordan.rivera@example.invalid",
        avatarURL: nil,
        emailShowNotifications: true,
        pushShowNotifications: true,
        comedianOnboardingCompleted: true,
        zipCode: "10012",
        nearbyDistanceMiles: 25,
        notificationsUnreadCount: 1
    )

    let favoriteComedians = ["Taylor Tomlinson", "Sam Jay"]
    let upcomingSavedShows = [
        Self.savedShow(
            id: 41_001,
            title: "Atsuko Okatsuka: Full Grown Tour",
            club: "Town Hall",
            city: "New York",
            date: "2026-08-21T20:00:00-04:00",
            imageURL: "https://laughtrack.b-cdn.net/comedians/Atsuko%20Okatsuka.png"
        ),
        Self.savedShow(
            id: 41_002,
            title: "Josh Johnson and Friends",
            club: "The Bell House",
            city: "Brooklyn",
            date: "2026-08-24T20:00:00-04:00",
            imageURL: "https://laughtrack.b-cdn.net/comedians/Josh%20Johnson.png"
        ),
        Self.savedShow(
            id: 41_003,
            title: "Taylor Tomlinson Live",
            club: "The Comedy Cellar",
            city: "New York",
            date: "2026-08-28T20:00:00-04:00",
            imageURL: "https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg"
        ),
        Self.savedShow(
            id: 41_004,
            title: "Sam Jay: Testing Material",
            club: "Union Hall",
            city: "Brooklyn",
            date: "2026-09-02T19:30:00-04:00",
            imageURL: "https://laughtrack.b-cdn.net/comedians/Sam%20Jay.png"
        ),
        Self.savedShow(
            id: 41_005,
            title: "Mike Birbiglia: Please Stop the Ride",
            club: "Beacon Theatre",
            city: "New York",
            date: "2026-09-05T20:00:00-04:00",
            imageURL: "https://laughtrack.b-cdn.net/comedian-images/246654/da23a0ff-061c-4a8b-82b8-e8b197615ad7/avatar.jpg"
        ),
        Self.savedShow(
            id: 41_006,
            title: "Michelle Wolf and Friends",
            club: "Gotham Comedy Club",
            city: "New York",
            date: "2026-09-08T20:00:00-04:00"
        ),
    ]
    let favoriteClubs = ["The Comedy Cellar"]
    let favoritePodcasts = ["Good One: A Podcast About Jokes"]

    let notifications = [
        NotificationCenterItem(
            id: "screenshot-notification-1",
            title: "Taylor Tomlinson has a show near you",
            body: "The Comedy Cellar on Saturday at 8:00 PM",
            comedians: [.init(id: 101, name: "Taylor Tomlinson", showIDs: [41001])],
            channels: ["push", "email"],
            showDate: Self.date("2026-07-19T00:00:00Z"),
            sentAt: Self.date("2026-07-15T17:00:00Z"),
            isUnread: true
        ),
        NotificationCenterItem(
            id: "screenshot-notification-2",
            title: "Your favorites have 2 new shows",
            body: "The Comedy Cellar and The Bell House",
            comedians: [
                .init(id: 101, name: "Taylor Tomlinson", showIDs: [41002]),
                .init(id: 102, name: "Sam Jay", showIDs: [41003]),
            ],
            channels: ["push"],
            showDate: Self.date("2026-07-19T23:30:00Z"),
            sentAt: Self.date("2026-07-14T19:00:00Z"),
            isUnread: false
        ),
    ]

    static var active: AuthenticatedScreenshotPersona? {
        #if DEBUG
        guard ProcessInfo.processInfo.environment[launchEnvironmentKey] == "1" else { return nil }
        return .shared
        #else
        return nil
        #endif
    }

    private static func date(_ value: String) -> Date {
        ISO8601DateFormatter().date(from: value)!
    }

    private static func savedShow(
        id: Int,
        title: String,
        club: String,
        city: String,
        date: String,
        imageURL: String = ""
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: id,
            clubId: id + 1_000,
            clubName: club,
            clubCity: city,
            clubState: "NY",
            date: Self.date(date),
            tickets: [
                .init(
                    price: 30,
                    purchaseUrl: "https://laughtrack.app/screenshot/tickets/\(id)",
                    soldOut: false,
                    _type: "General admission"
                ),
            ],
            name: title,
            imageUrl: imageURL,
            soldOut: false,
            timezone: "America/New_York"
        )
    }

    static func == (lhs: AuthenticatedScreenshotPersona, rhs: AuthenticatedScreenshotPersona) -> Bool {
        lhs.user == rhs.user
            && lhs.favoriteComedians == rhs.favoriteComedians
            && lhs.upcomingSavedShows == rhs.upcomingSavedShows
            && lhs.favoriteClubs == rhs.favoriteClubs
            && lhs.favoritePodcasts == rhs.favoritePodcasts
            && lhs.notifications == rhs.notifications
    }
}
