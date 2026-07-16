import Foundation
import LaughTrackCore

/// Credentials-free, immutable content used only by explicit screenshot launches.
/// Keeping this at the view boundary prevents capture runs from touching auth or
/// mutable production APIs while still rendering the real authenticated pages.
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
        (title: "Taylor Tomlinson", detail: "Tonight · The Bell House"),
        (title: "Sam Jay", detail: "Friday · Comedy Cellar"),
    ]

    let notifications = [
        NotificationCenterItem(
            id: "screenshot-notification-1",
            title: "Taylor Tomlinson has a show near you",
            body: "Tonight at The Bell House",
            tap: .show(41001),
            channels: ["push", "email"],
            showDate: Self.date("2026-07-18T20:00:00Z"),
            sentAt: nil,
            isUnread: true
        ),
        NotificationCenterItem(
            id: "screenshot-notification-2",
            title: "Your favorites have 2 new shows",
            body: "Sam Jay and Taylor Tomlinson added dates nearby",
            tap: .favorites([41002, 41003]),
            channels: ["push"],
            showDate: Self.date("2026-07-19T20:00:00Z"),
            sentAt: nil,
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
            && lhs.notifications == rhs.notifications
    }
}
