import SwiftUI
import LaughTrackCore
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIURLSession
import Foundation

// SwiftPM test bundles provide their own entrypoint; keep the app entrypoint for Xcode builds.
#if !SWIFT_PACKAGE
@main
struct LaughTrackApp: App {
    @StateObject private var coordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var authManager: AuthManager

    private let container: ServiceContainer
    private let apiClient: Client
    private let theme: LaughTrackTheme

    init() {
        Self.resetPersistentStateForUITestsIfNeeded()
        let bootstrap = AppBootstrap()
        self.container = bootstrap.container
        self.apiClient = bootstrap.apiClient
        self.theme = bootstrap.theme
        _authManager = StateObject(wrappedValue: bootstrap.authManager)
    }

    var body: some Scene {
        WindowGroup {
            ContentView(apiClient: apiClient)
                .environment(\.appTheme, theme)
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
                .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        }
    }

    private static func resetPersistentStateForUITestsIfNeeded() {
        guard ProcessInfo.processInfo.arguments.contains("UITEST_RESET_STATE") else { return }

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "laughtrack.discovery.nearby-preference")
        defaults.removeObject(forKey: "laughtrack.discovery.home-nearby-prompt-dismissed")
        defaults.removeObject(forKey: "laughtrack.auth.session-metadata")
    }
}
#endif
