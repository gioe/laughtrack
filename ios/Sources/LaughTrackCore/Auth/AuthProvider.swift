import Foundation

public enum AuthProvider: String, CaseIterable, Codable, Equatable, Sendable {
    case apple
    case google
    case email

    public var title: String {
        switch self {
        case .apple:
            "Continue with Apple"
        case .google:
            "Continue with Google"
        case .email:
            "Email me a sign-in link"
        }
    }

    public var subtitle: String {
        switch self {
        case .apple:
            "Use your Apple ID to sign in quickly."
        case .google:
            "Use the Google account you already use on the web."
        case .email:
            "Use LaughTrack’s existing magic-link email sign-in."
        }
    }

    public var symbolName: String {
        switch self {
        case .apple:
            "apple.logo"
        case .google:
            "globe"
        case .email:
            "envelope.fill"
        }
    }

    public var displayName: String {
        rawValue.capitalized
    }
}
