import SwiftUI
import LaughTrackCore
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIURLSession
import Foundation
import os
#if canImport(UIKit)
import UIKit
#endif

// SwiftPM test bundles provide their own entrypoint; keep the app entrypoint for Xcode builds.
#if !SWIFT_PACKAGE
@main
struct LaughTrackApp: App {
    @StateObject private var coordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var authManager: AuthManager
    @StateObject private var loginModalPresenter = LoginModalPresenter()
    @StateObject private var clubFavorites = ClubFavoriteStore()
    #if canImport(UIKit)
    @UIApplicationDelegateAdaptor(LaughTrackRemoteNotificationDelegate.self) private var remoteNotificationDelegate
    #endif

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
        #if canImport(UIKit)
        remoteNotificationDelegate.pushTokenManager = bootstrap.container.resolveOptional((any PushDeviceTokenManaging).self)
        #endif

        // App.init is the only once-per-cold-launch hook the soft prompt
        // cadence has — feeds the sessionCountSinceLastDeferral gate. Skip
        // under mock mode so UI-test and screenshot launches don't silently
        // mutate persisted soft-prompt state.
        if !MockModeDetector.isMockMode {
            bootstrap.container.resolve(PushPermissionStateStore.self).recordColdLaunchSession()
        } else {
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
                .environmentObject(clubFavorites)
                .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
                .preferredColorScheme(.dark)
        }
    }

    private static func resetPersistentStateForUITestsIfNeeded() {
        let arguments = ProcessInfo.processInfo.arguments
        guard arguments.contains("UITEST_RESET_STATE") || arguments.contains(MockModeDetector.mockModeArgument) else { return }

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "laughtrack.discovery.nearby-preference")
        defaults.removeObject(forKey: "laughtrack.discovery.home-nearby-prompt-dismissed")
        defaults.removeObject(forKey: "laughtrack.auth.session-metadata")
        defaults.removeObject(forKey: FirstEntryAuthChoiceStore.storageKey)
    }

    /// In mock mode, pre-populate the saved nearby preference to Hollywood (90028)
    /// so the Near Me screen renders LA shows deterministically. Without this seed,
    /// the discovery rails fall back to IP-based geolocation which leaks the
    /// developer's home location into App Store screenshots. Also pre-record the
    /// first-entry guest-browsing choice so the screenshot lane doesn't capture
    /// the "Find your next laugh" auth gate as its first frame.
    private static func applyMockModeSeedData(container: ServiceContainer) {
        let store = container.resolve(NearbyPreferenceStore.self)
        store.setManualZip("90028", distanceMiles: 25, city: "Los Angeles", state: "CA")
        UserDefaults.standard.set(true, forKey: FirstEntryAuthChoiceStore.storageKey)
    }
}
#endif

#if canImport(UIKit)
final class LaughTrackRemoteNotificationDelegate: NSObject, UIApplicationDelegate {
    private static let logger = Logger(
        subsystem: "com.laughtrack.notifications",
        category: "RemoteNotifications"
    )

    var pushTokenManager: (any PushDeviceTokenManaging)?

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        Task {
            await pushTokenManager?.uploadDeviceToken(deviceToken)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        Self.logger.error(
            "Remote notification registration failed: \(error.localizedDescription, privacy: .public)"
        )
    }
}
#endif
