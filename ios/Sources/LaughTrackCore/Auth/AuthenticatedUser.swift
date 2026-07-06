import Foundation

public struct AuthenticatedUser: Equatable, Sendable {
    /// Opaque server-issued user identifier (User.id, surfaced by GET /v1/me).
    /// Passed verbatim to analytics setUserID — it survives email/displayName
    /// changes. Required: every /v1/me response carries it (TASK-2612 rollout
    /// complete), so construction sites must always supply one.
    public let userId: String
    public let displayName: String?
    public let email: String
    public let avatarURL: URL?
    /// Whether the signed-in user has the admin role server-side
    /// (`UserProfile.role === "admin"`). Surfaced through `/v1/me`. Used to
    /// gate admin-only UI affordances (e.g. the show-ID badge on the
    /// show-detail header). Defaults to `false` so non-API construction sites
    /// (tests, signed-out fallbacks) stay unaffected.
    public let isAdmin: Bool
    public let emailShowNotifications: Bool
    public let pushShowNotifications: Bool
    public let comedianOnboardingCompleted: Bool
    public let zipCode: String?
    public let nearbyDistanceMiles: Int?
    /// Number of unread notifications surfaced by `/v1/me`
    /// (`notificationsUnreadCount`). Drives the profile-button unread badge so
    /// it can render from the launch-time `/me` fetch without loading the full
    /// notification feed. Defaults to `0` so non-API construction sites (tests,
    /// signed-out fallbacks, older `/v1/me` responses that omit the field) stay
    /// unaffected.
    public let notificationsUnreadCount: Int

    public init(
        userId: String,
        displayName: String?,
        email: String,
        avatarURL: URL?,
        isAdmin: Bool = false,
        emailShowNotifications: Bool = false,
        pushShowNotifications: Bool = false,
        comedianOnboardingCompleted: Bool = false,
        zipCode: String? = nil,
        nearbyDistanceMiles: Int? = nil,
        notificationsUnreadCount: Int = 0
    ) {
        self.userId = userId
        self.displayName = displayName
        self.email = email
        self.avatarURL = avatarURL
        self.isAdmin = isAdmin
        self.emailShowNotifications = emailShowNotifications
        self.pushShowNotifications = pushShowNotifications
        self.comedianOnboardingCompleted = comedianOnboardingCompleted
        self.zipCode = zipCode
        self.nearbyDistanceMiles = nearbyDistanceMiles
        self.notificationsUnreadCount = notificationsUnreadCount
    }

    public func withComedianOnboardingCompleted(_ completed: Bool) -> AuthenticatedUser {
        AuthenticatedUser(
            userId: userId,
            displayName: displayName,
            email: email,
            avatarURL: avatarURL,
            isAdmin: isAdmin,
            emailShowNotifications: emailShowNotifications,
            pushShowNotifications: pushShowNotifications,
            comedianOnboardingCompleted: completed,
            zipCode: zipCode,
            nearbyDistanceMiles: nearbyDistanceMiles,
            notificationsUnreadCount: notificationsUnreadCount
        )
    }
}
