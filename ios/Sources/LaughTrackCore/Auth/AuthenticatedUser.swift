import Foundation

public struct AuthenticatedUser: Equatable, Sendable {
    public let displayName: String?
    public let email: String
    public let avatarURL: URL?

    public init(displayName: String?, email: String, avatarURL: URL?) {
        self.displayName = displayName
        self.email = email
        self.avatarURL = avatarURL
    }
}
