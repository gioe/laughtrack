import Foundation

public struct AuthenticatedUser: Equatable, Sendable {
    public let displayName: String?
    public let email: String
    public let avatarURL: URL?
    public let emailShowNotifications: Bool
    public let pushShowNotifications: Bool
    public let zipCode: String?
    public let nearbyDistanceMiles: Int?

    public init(
        displayName: String?,
        email: String,
        avatarURL: URL?,
        emailShowNotifications: Bool = false,
        pushShowNotifications: Bool = false,
        zipCode: String? = nil,
        nearbyDistanceMiles: Int? = nil
    ) {
        self.displayName = displayName
        self.email = email
        self.avatarURL = avatarURL
        self.emailShowNotifications = emailShowNotifications
        self.pushShowNotifications = pushShowNotifications
        self.zipCode = zipCode
        self.nearbyDistanceMiles = nearbyDistanceMiles
    }
}
