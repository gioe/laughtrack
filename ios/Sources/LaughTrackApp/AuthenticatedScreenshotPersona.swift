import Foundation
import LaughTrackCore

/// Credentials-free, immutable content used only by explicit screenshot launches.
/// Keeping this at the view boundary prevents capture runs from touching auth or
/// mutable production APIs while still rendering the real authenticated pages.
/// Remote artwork is intentionally absent so both platforms exercise their
/// branded, deterministic fallback policy instead of a network image cache.
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
    let favoriteShows = [
        (title: "Taylor Tomlinson Live", detail: "July 18 · The Comedy Cellar · New York"),
        (title: "Sam Jay Live", detail: "July 19 · The Bell House · Brooklyn"),
    ]
    let upcomingSavedShows = [
        (title: "Atsuko Okatsuka: Full Grown Tour", detail: "July 21 · Town Hall · New York"),
        (title: "Josh Johnson and Friends", detail: "July 24 · The Bell House · Brooklyn"),
    ]
    let pastSavedShows = [
        (title: "Sam Jay: Testing Material", detail: "July 10 · Union Hall · Brooklyn"),
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

    static func == (lhs: AuthenticatedScreenshotPersona, rhs: AuthenticatedScreenshotPersona) -> Bool {
        lhs.user == rhs.user
            && lhs.favoriteComedians == rhs.favoriteComedians
            && lhs.favoriteShows.map(\.title) == rhs.favoriteShows.map(\.title)
            && lhs.favoriteShows.map(\.detail) == rhs.favoriteShows.map(\.detail)
            && lhs.upcomingSavedShows.map(\.title) == rhs.upcomingSavedShows.map(\.title)
            && lhs.upcomingSavedShows.map(\.detail) == rhs.upcomingSavedShows.map(\.detail)
            && lhs.pastSavedShows.map(\.title) == rhs.pastSavedShows.map(\.title)
            && lhs.pastSavedShows.map(\.detail) == rhs.pastSavedShows.map(\.detail)
            && lhs.favoriteClubs == rhs.favoriteClubs
            && lhs.favoritePodcasts == rhs.favoritePodcasts
            && lhs.notifications == rhs.notifications
    }
}
