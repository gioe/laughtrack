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
            emailShowNotifications: emailShowNotifications,
            pushShowNotifications: pushShowNotifications,
            comedianOnboardingCompleted: completed,
            zipCode: zipCode,
            nearbyDistanceMiles: nearbyDistanceMiles
        )
    }
}
