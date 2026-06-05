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
                #if DEBUG
                .task {
                    guard let route = DebugLaunchRoute.routeFromEnvironment() else { return }
                    coordinator.push(route)
                }
                #endif
        }
    }

    private static func resetPersistentStateForUITestsIfNeeded() {
        let arguments = ProcessInfo.processInfo.arguments
        guard arguments.contains(UITestLaunchArgs.resetState) || arguments.contains(MockModeDetector.mockModeArgument) else { return }

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "laughtrack.discovery.nearby-preference")
        defaults.removeObject(forKey: "laughtrack.discovery.home-nearby-prompt-dismissed")
        defaults.removeObject(forKey: "laughtrack.auth.session-metadata")
        defaults.removeObject(forKey: FirstEntryAuthChoiceStore.storageKey)
        // Soft push-prompt cadence state (deferralCount, lastDeferredAt,
        // postOnboardingFavoriteCount, sessionCountSinceLastDeferral). Reset so
        // the soft-prompt test_sim suite starts deterministically from a fresh
        // cadence regardless of prior test-run residue on the sim sandbox.
        defaults.removeObject(forKey: PushPermissionStateStore.storageKey)

        // The block above wipes the first-entry guest choice, which is correct
        // for tests that exercise the auth gate. Tests that need the shell to
        // mount directly (e.g. the soft push-prompt cadence suite, which has
        // no business with the auth gate) can opt back in by setting
        // UITestLaunchArgs.guestBrowsing — re-seed after the wipe so the
        // order of args doesn't matter.
        if arguments.contains(UITestLaunchArgs.guestBrowsing) {
            defaults.set(true, forKey: FirstEntryAuthChoiceStore.storageKey)
        }
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

#if DEBUG
/// UI-test seam for the soft push-prompt cadence suite. The favorite-tap flow
/// requires a signed-in user + a live POST /favorites round-trip, neither of
/// which is feasible in a test_sim run inside the 90s tool timeout. Synthesize
/// the post-onboarding favorite signals at app start instead, so the test
/// exercises the AppShellView → SoftPushPromptCoordinator → PushPermissionStateStore
/// wiring (and the cadence's Inputs construction) end-to-end without standing
/// up auth or the favorites API. Fires once per process — the test relaunches
/// the app to start a fresh process when it needs a second round of signals.
@MainActor
enum DebugSimulatedFavoriteHook {
    static let environmentKey = UITestLaunchArgs.simulatePostOnboardingFavoriteCount

    private static var hasFired = false

    static func favoriteCount(processInfo: ProcessInfo = .processInfo) -> Int? {
        guard let raw = processInfo.environment[environmentKey] else { return nil }
        return Int(raw)
    }

    static func fireIfRequested(coordinator: SoftPushPromptCoordinator) async {
        guard !hasFired else { return }
        guard let count = favoriteCount(), count > 0 else { return }
        hasFired = true
        for _ in 0..<count {
            await coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        }
    }
}

/// Parses `LAUNCHTRACK_DEBUG_ROUTE` (e.g. `podcast:30`) into an `AppRoute` so a
/// dev build can be relaunched onto a specific entity detail screen without
/// editing source. Wired into `LaughTrackApp.body` as a DEBUG-only `.task` on
/// `ContentView`; never compiled into release builds.
enum DebugLaunchRoute {
    static let environmentKey = "LAUNCHTRACK_DEBUG_ROUTE"

    static func routeFromEnvironment(processInfo: ProcessInfo = .processInfo) -> AppRoute? {
        guard let raw = processInfo.environment[environmentKey] else { return nil }
        return parse(raw)
    }

    static func parse(_ raw: String) -> AppRoute? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let separator = trimmed.firstIndex(of: ":") else { return nil }
        let kind = trimmed[..<separator].lowercased()
        let idString = trimmed[trimmed.index(after: separator)...].trimmingCharacters(in: .whitespaces)
        guard let id = Int(idString) else { return nil }
        switch kind {
        case "podcast", "podcasts", "podcastdetail":
            return .podcastDetail(id)
        case "show", "shows", "showdetail":
            return .showDetail(id)
        case "comedian", "comedians", "comediandetail":
            return .comedianDetail(id)
        case "club", "clubs", "clubdetail":
            return .clubDetail(id)
        default:
            return nil
        }
    }
}

/// DEBUG-only hard jump into the post-auth comedian onboarding surface. Unlike
/// `FORCE_COMEDIAN_ONBOARDING`, this bypasses auth/session state entirely so a
/// developer can iterate on the screen in a simulator with no saved account.
enum DebugComedianOnboardingLaunch {
    static let environmentKey = UITestLaunchArgs.forceComedianOnboardingScreen

    static func shouldForceScreen(processInfo: ProcessInfo = .processInfo) -> Bool {
        processInfo.environment[environmentKey] == "1"
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
