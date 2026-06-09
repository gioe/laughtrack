import Foundation

public struct AuthenticatedUser: Equatable, Sendable {
    /// Opaque server-issued user identifier (User.id, surfaced by GET /v1/me).
    /// Preferred over the SHA-256 email hash for analytics setUserID because it
    /// survives email/displayName changes. Nullable so older /v1/me responses
    /// that predate TASK-2612 still decode cleanly; the AppBootstrap analytics
    /// sink falls back to the email hash when this is nil.
    public let userId: String?
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

    public init(
        userId: String? = nil,
        displayName: String?,
        email: String,
        avatarURL: URL?,
        isAdmin: Bool = false,
        emailShowNotifications: Bool = false,
        pushShowNotifications: Bool = false,
        comedianOnboardingCompleted: Bool = false,
        zipCode: String? = nil,
        nearbyDistanceMiles: Int? = nil
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
            nearbyDistanceMiles: nearbyDistanceMiles
        )
    }
}
