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
    ///
    /// New toolbar actions whose decision logic branches on app state should
    /// add a sibling `*ToolbarTarget(...)` helper here and unit-test the
    /// resolution directly (see `ContentViewNavigationTests`
    /// `homeSettingsButtonPushesSettingsRoute` for the canonical pattern: assert
    /// the button mounts with its accessibility id, then exercise the resolver
    /// without `accessibilityActivate()`). The TASK-1767 audit confirmed
    /// `HomeView` is the only `.toolbar { ... }` site in `ios/Sources/` at the
    /// time of writing — `LaughTrackNavigationChrome`'s `.toolbarBackground`
    /// calls are styling-only and have no actions to extract.
    static func homeToolbarTarget(isSignedIn: Bool) -> AppRoute {
        isSignedIn ? .settings : .profile
    }
}
