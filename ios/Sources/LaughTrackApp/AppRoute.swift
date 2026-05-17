enum AppRoute: Hashable, Codable {
    case nearMe
    case search
    case library
    case profile
    case showDetail(Int)
    case comedianDetail(Int)
    case clubDetail(Int)
    case podcastDetail(Int)

    var shellTab: AppTab? {
        switch self {
        case .nearMe:
            return .nearMe
        case .search:
            return .search
        case .library:
            return .favorites
        case .profile, .showDetail, .comedianDetail, .clubDetail, .podcastDetail:
            return nil
        }
    }

    /// Route the near-me toolbar button pushes when tapped. Extracted so test code can assert the
    /// resolution without driving the SwiftUI toolbar item via accessibility,
    /// which under iOS 26 / Xcode 26 doesn't activate reliably inside HostedView.
    ///
    /// New toolbar actions whose decision logic branches on app state should
    /// add a sibling `*ToolbarTarget(...)` helper here and unit-test the
    /// resolution directly (see `ContentViewNavigationTests`
    /// `nearMeSettingsButtonPushesSettingsRoute` for the canonical pattern: assert
    /// the button mounts with its accessibility id, then exercise the resolver
    /// without `accessibilityActivate()`). The TASK-1767 audit confirmed
    /// `HomeView` is the only `.toolbar { ... }` site in `ios/Sources/` at the
    /// time of writing — `LaughTrackNavigationChrome`'s `.toolbarBackground`
    /// calls are styling-only and have no actions to extract.
    static func nearMeToolbarTarget(isSignedIn: Bool) -> AppRoute {
        .profile
    }

    static func accountHeaderTarget() -> AppRoute {
        .profile
    }
}
