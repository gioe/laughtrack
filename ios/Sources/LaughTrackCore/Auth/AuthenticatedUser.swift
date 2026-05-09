import Foundation

public struct AuthenticatedUser: Equatable, Sendable {
    public let displayName: String?
    public let email: String
    public let avatarURL: URL?
    public let emailShowNotifications: Bool
    public let pushShowNotifications: Bool
    public let comedianOnboardingCompleted: Bool
    public let zipCode: String?
    public let nearbyDistanceMiles: Int?

    public init(
        displayName: String?,
        email: String,
        avatarURL: URL?,
        emailShowNotifications: Bool = false,
        pushShowNotifications: Bool = false,
        comedianOnboardingCompleted: Bool = false,
        zipCode: String? = nil,
        nearbyDistanceMiles: Int? = nil
    ) {
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
