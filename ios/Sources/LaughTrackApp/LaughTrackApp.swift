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
    @StateObject private var loginModalPresenter = LoginModalPresenter()

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

        if MockModeDetector.isMockMode {
            Self.applyMockModeSeedData(container: bootstrap.container)
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView(apiClient: apiClient)
                .environment(\.appTheme, theme)
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
                .environmentObject(loginModalPresenter)
                .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        }
    }

    private static func resetPersistentStateForUITestsIfNeeded() {
        let arguments = ProcessInfo.processInfo.arguments
        guard arguments.contains("UITEST_RESET_STATE") || arguments.contains(MockModeDetector.mockModeArgument) else { return }

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "laughtrack.discovery.nearby-preference")
        defaults.removeObject(forKey: "laughtrack.discovery.home-nearby-prompt-dismissed")
        defaults.removeObject(forKey: "laughtrack.auth.session-metadata")
    }

    /// In mock mode, pre-populate the saved nearby preference to Hollywood (90028)
    /// so the Near Me screen renders LA shows deterministically. Without this seed,
    /// the discovery rails fall back to IP-based geolocation which leaks the
    /// developer's home location into App Store screenshots.
    private static func applyMockModeSeedData(container: ServiceContainer) {
        let store = container.resolve(NearbyPreferenceStore.self)
        store.setManualZip("90028", distanceMiles: 25, city: "Los Angeles", state: "CA")
    }
}
#endif
