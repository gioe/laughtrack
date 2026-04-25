enum AppRoute: Hashable, Codable {
    case home
    case search
    case library
    case profile
    case settings
    case showDetail(Int)
    case comedianDetail(Int)
    case clubDetail(Int)

    /// Route the home-tab toolbar button pushes when tapped: `.settings` when
    /// the user is signed in (the icon is a gear), `.profile` when signed out
    /// (the icon prompts sign-in). Extracted so test code can assert the
    /// resolution without driving the SwiftUI toolbar item via accessibility,
    /// which under iOS 26 / Xcode 26 doesn't activate reliably inside HostedView.
    static func homeToolbarTarget(isSignedIn: Bool) -> AppRoute {
        isSignedIn ? .settings : .profile
    }
}
