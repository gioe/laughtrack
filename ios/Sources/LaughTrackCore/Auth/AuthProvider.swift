import Foundation

public enum AuthProvider: String, CaseIterable, Codable, Equatable, Sendable {
    case apple
    case google

    public var title: String {
        switch self {
        case .apple:
            "Continue with Apple"
        case .google:
            "Continue with Google"
        }
    }

    public var subtitle: String {
        switch self {
        case .apple:
            "Use your Apple ID to sign in quickly."
        case .google:
            "Use the Google account you already use on the web."
        }
    }

    public var symbolName: String {
        switch self {
        case .apple:
            "apple.logo"
        case .google:
            "globe"
        }
    }

    public var displayName: String {
        rawValue.capitalized
    }
}
