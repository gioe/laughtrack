import SwiftUI
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient
#if canImport(UIKit)
import UIKit
#endif

enum LaughTrackViewTestID {
    static let homeScreen = "laughtrack.home.screen"
    static let searchTabScreen = "laughtrack.search-tab.screen"
    static let searchHeader = "laughtrack.search.header"
    static let primitiveFilterScroller = "laughtrack.primitive-filter.scroller"
    static let searchRootField = "laughtrack.search.field"
    static let favoritesTabScreen = "laughtrack.favorites-tab.screen"
    static let libraryTabScreen = favoritesTabScreen
    static let profileTabScreen = "laughtrack.profile-tab.screen"
    static let profileHero = "laughtrack.profile.hero"
    static let profileSettingsPanel = "laughtrack.profile.settings-panel"
    static let profileDeleteAccountButton = "laughtrack.profile.delete-account-button"
    static let settingsNotificationsSection = "laughtrack.settings.notifications.section"
    static let settingsFavoriteComedianEmailAlertsToggle = "laughtrack.settings.notifications.favorite-comedian-email-alerts"
    static let settingsFavoriteComedianPushAlertsToggle = "laughtrack.settings.notifications.favorite-comedian-push-alerts"
    static let onboardingScreen = "laughtrack.onboarding.screen"
    static let onboardingSearchField = "laughtrack.onboarding.search-field"
    static let onboardingSearchButton = "laughtrack.onboarding.search-button"
    static let onboardingFavoriteCount = "laughtrack.onboarding.favorite-count"
    static let onboardingEmailToggle = "laughtrack.onboarding.email-toggle"
    static let onboardingPushToggle = "laughtrack.onboarding.push-toggle"
    static let onboardingContinueButton = "laughtrack.onboarding.continue-button"
    static let onboardingSkipButton = "laughtrack.onboarding.skip-button"
    static let softPushPromptEnableButton = "laughtrack.soft-push-prompt.enable-button"
    static let softPushPromptDeferButton = "laughtrack.soft-push-prompt.defer-button"
    static let accountHeaderButton = "laughtrack.account.header-button"
    static let accountNotificationsMenuItem = "laughtrack.account.menu.notifications"
    static let accountSettingsMenuItem = "laughtrack.account.menu.settings"
    static let notificationCenterScreen = "laughtrack.notifications.screen"
    static let notificationRow = "laughtrack.notifications.row"
    static let locationPermissionPitch = "laughtrack.location-permission.pitch"
    static let locationPermissionAllowButton = "laughtrack.location-permission.allow-button"
    static let locationPermissionManualZipButton = "laughtrack.location-permission.manual-zip-button"
    static let locationPermissionCloseButton = "laughtrack.location-permission.close-button"
    static let homeSettingsButton = "laughtrack.home.settings-button"
    static let homeShowsSearchButton = "laughtrack.home.shows-search-button"
    static let homeClubsSearchButton = "laughtrack.home.clubs-search-button"
    static let homeComediansSearchButton = "laughtrack.home.comedians-search-button"
    static let homeDiscoverHeader = "laughtrack.home.discover-header"
    static let homeLocationPrompt = "laughtrack.home.location-prompt"
    static let homeLocationSheet = "laughtrack.home.location-sheet"
    static let homeLocationZipField = "laughtrack.home.location.zip-field"
    static let homeLocationDistancePicker = "laughtrack.home.location.distance-picker"
    static let homeLocationApplyButton = "laughtrack.home.location.apply-button"
    static let homeLocationCurrentButton = "laughtrack.home.location.current-button"
    static let homeLocationClearButton = "laughtrack.home.location.clear-button"
    static let homeShowsTonightRail = "laughtrack.home.shows-tonight-rail"
    static let homeShowsTonightHeroButton = "laughtrack.home.shows-tonight-hero-button"
    static let homeShowsTonightSeeMoreButton = "laughtrack.home.shows-tonight-see-more-button"
    static let homeTrendingComediansRail = "laughtrack.home.trending-comedians-rail"
    static let homePopularClubsRail = "laughtrack.home.popular-clubs-rail"
    static let homeTrendingPodcastsRail = "laughtrack.home.trending-podcasts-rail"
    static let showsSearchScreen = "laughtrack.shows-search.screen"
    static let clubsSearchScreen = "laughtrack.clubs-search.screen"
    static let comediansSearchScreen = "laughtrack.comedians-search.screen"
    static let showDetailScreen = "laughtrack.show-detail.screen"
    static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
    static let podcastDetailScreen = "laughtrack.podcast-detail-screen"
    static let comedianDetailTabPicker = "laughtrack.comedian-detail.tab-picker"
    static let podcastMiniPlayer = "laughtrack.podcast-mini-player"
    static let clubDetailScreen = "laughtrack.club-detail.screen"
    static let settingsNearbyEmptyState = "laughtrack.settings.nearby.empty-state"
    static let settingsNearbySavedState = "laughtrack.settings.nearby.saved-state"
    static let settingsZipField = "laughtrack.settings.zip-field"
    static let settingsDistancePicker = "laughtrack.settings.distance-picker"
    static let settingsSaveButton = "laughtrack.settings.save-button"
    static let settingsClearButton = "laughtrack.settings.clear-button"
    static let favoritesHeader = "laughtrack.favorites.header"
    static let favoritesComediansSection = "laughtrack.favorites.comedians-section"
    static let favoritesShowsSection = "laughtrack.favorites.shows-section"
    static let favoritesClubsSection = "laughtrack.favorites.clubs-section"
    static let favoritesPodcastsSection = "laughtrack.favorites.podcasts-section"
    static let libraryFavoritesSection = favoritesComediansSection
    static let firstEntryAuthChoiceScreen = "laughtrack.auth-choice.screen"
    static let firstEntryContinueAsGuestButton = "laughtrack.auth-choice.continue-as-guest"

    static func firstEntryAuthOptionButton(_ provider: AuthProvider) -> String {
        "laughtrack.auth-choice.option.\(provider.rawValue)"
    }

    static func showsSearchResultButton(_ id: Int) -> String {
        "laughtrack.shows-search.result-\(id)"
    }

    static func comediansSearchResultButton(_ id: Int) -> String {
        "laughtrack.comedians-search.result-\(id)"
    }

    static func onboardingComedianRow(_ id: Int) -> String {
        "laughtrack.onboarding.comedian-row-\(id)"
    }

    static func onboardingComedianFavoriteButton(_ id: Int) -> String {
        "laughtrack.onboarding.comedian-favorite-\(id)"
    }

    static func homeTrendingComedianButton(_ id: Int) -> String {
        "laughtrack.home.trending-comedian-\(id)"
    }

    static func homeTrendingPodcastButton(_ id: Int) -> String {
        "laughtrack.home.trending-podcast-\(id)"
    }

    static func homeFavoriteShowButton(_ id: Int) -> String {
        "laughtrack.home.favorite-show-\(id)"
    }

    static func homeShowsTonightButton(_ id: Int) -> String {
        "laughtrack.home.shows-tonight-\(id)"
    }

    static func clubsSearchResultButton(_ id: Int) -> String {
        "laughtrack.clubs-search.result-\(id)"
    }

    static func podcastsSearchResultButton(_ id: String) -> String {
        "laughtrack.podcasts-search.result-\(id)"
    }

    static func primitiveFilterButton(_ primitive: String) -> String {
        "laughtrack.primitive-filter.\(primitive)"
    }
}

struct ContentView: View {
    static let firstEntrySignedOutAuthOptions = ProfileView.signedOutAuthOptions

    enum RootSurface: Equatable {
        case loading
        case authChoiceGate(message: String?)
        case signedOutShell(message: String?)
        case authenticatedShell
        case comedianOnboarding
    }

    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var favorites = ComedianFavoriteStore()
    @StateObject private var podcastFavorites = PodcastFavoriteStore()
    @StateObject private var shellState = AppShellState()
    @StateObject private var firstEntryAuthChoiceStore = FirstEntryAuthChoiceStore()
    @StateObject private var podcastPlayer = PodcastPlaybackController()
    @State private var hasLoadedInitialHome = false
    @Namespace private var authLogoNamespace

    var body: some View {
        let surface = Self.rootSurface(
            authState: authManager.state,
            hasLoadedCurrentUser: authManager.hasLoadedCurrentUser,
            currentUser: authManager.currentUser,
            hasResolvedFirstEntryChoice: firstEntryAuthChoiceStore.hasResolvedFirstEntryChoice
        )

        Group {
            switch surface {
            case .loading:
                AuthLoadingView(logoNamespace: authLogoNamespace)
                    .transition(.opacity)
            case .authChoiceGate(let message):
                FirstEntryAuthChoiceView(
                    message: message,
                    logoNamespace: authLogoNamespace,
                    continueAsGuest: firstEntryAuthChoiceStore.continueAsGuest,
                    signIn: { provider in
                        Task {
                            await authManager.signIn(with: provider)
                        }
                    }
                )
                .transition(.opacity.combined(with: .scale(scale: 0.985, anchor: .center)))
            case .signedOutShell(let message):
                appShell(signedOutMessage: message)
                    .transition(.opacity)
            case .comedianOnboarding:
                ComedianOnboardingView(
                    apiClient: apiClient,
                    favorites: favorites
                )
                .environmentObject(favorites)
                .transition(.opacity)
            case .authenticatedShell:
                appShell(signedOutMessage: nil)
                    .transition(.opacity)
            }
        }
        .overlay {
            if Self.shouldShowLaunchSplash(
                surface: surface,
                hasLoadedInitialHome: hasLoadedInitialHome,
                isHomeTabSelected: shellState.selectedTab == .nearMe
            ) {
                AuthLoadingView(logoNamespace: authLogoNamespace)
                    .transition(.opacity)
            }
        }
        .tint(theme.colors.primary)
        .laughTrackKeyboardDismissToolbar()
        .animation(.easeInOut(duration: 0.42), value: surface)
        .animation(.easeInOut(duration: 0.42), value: hasLoadedInitialHome)
        .task {
            await authManager.restoreSessionIfNeeded()
        }
        .onAppear {
            #if DEBUG
            if ProcessInfo.processInfo.environment[UITestLaunchArgs.forceLoginPrompt] == "1" {
                loginModalPresenter.present()
            }
            #endif
        }
        .onReceive(authManager.$state) { state in
            if case .authenticated = state {
                // Signing in resolves the first-entry choice, so a later sign-out
                // returns to the signed-out shell rather than the first-launch gate.
                // Also fires on session restore at launch, migrating users who signed
                // in on a pre-fix build.
                firstEntryAuthChoiceStore.markSignedIn()
            }

            guard case .signedOut(let message) = state,
                  message?.localizedCaseInsensitiveContains("session expired") == true
            else { return }

            loginModalPresenter.present()
        }
        .sheet(isPresented: $loginModalPresenter.isPresented) {
            LaughTrackLoginModalView()
        }
    }

    static func rootSurface(
        authState: AuthManager.State,
        hasLoadedCurrentUser: Bool,
        currentUser: AuthenticatedUser?,
        hasResolvedFirstEntryChoice: Bool = false,
        forceComedianOnboardingScreen: Bool = Self.forceComedianOnboardingScreenFromEnvironment()
    ) -> RootSurface {
        if forceComedianOnboardingScreen {
            return .comedianOnboarding
        }

        switch authState {
        case .restoring:
            return .loading
        case .signingIn:
            // First-entry auth gate keeps the logo loading view so the
            // matched-geometry "launch-logo" transition into AuthLoadingView
            // reads as intended. But once the user is browsing the shell (e.g.
            // tapping "Continue with Google" from Profile), don't blow the whole
            // UI away to the splash — keep the shell visible underneath the
            // ASWebAuthenticationSession sheet that's about to present.
            guard hasResolvedFirstEntryChoice else {
                return .loading
            }
            return .signedOutShell(message: nil)
        case .signedOut(let message):
            guard hasResolvedFirstEntryChoice else {
                return .authChoiceGate(message: message)
            }

            return .signedOutShell(message: message)
        case .authenticated:
            guard hasLoadedCurrentUser || currentUser != nil else {
                return .loading
            }

            if shouldPresentComedianOnboarding(authState: authState, currentUser: currentUser) {
                return .comedianOnboarding
            }

            return .authenticatedShell
        }
    }

    static func shouldShowLaunchSplash(
        surface: RootSurface,
        hasLoadedInitialHome: Bool,
        isHomeTabSelected: Bool
    ) -> Bool {
        guard !hasLoadedInitialHome, isHomeTabSelected else { return false }
        switch surface {
        case .signedOutShell, .authenticatedShell:
            return true
        case .loading, .authChoiceGate, .comedianOnboarding:
            return false
        }
    }

    static func shouldPresentComedianOnboarding(
        authState: AuthManager.State,
        currentUser: AuthenticatedUser?
    ) -> Bool {
        guard case .authenticated = authState,
              let currentUser
        else { return false }

#if DEBUG
        // FORCE_COMEDIAN_ONBOARDING=1 forces the comedian-onboarding screen
        // on every relaunch even when the signed-in user's server-side
        // `comedianOnboardingCompleted` is true. Mirrors the existing
        // `LAUNCHTRACK_DEBUG_ROUTE` env-var pattern; the key is centralized
        // in `UITestLaunchArgs.forceComedianOnboarding`. Compiled out of
        // release builds.
        if ProcessInfo.processInfo.environment[UITestLaunchArgs.forceComedianOnboarding] == "1" {
            return true
        }
#endif

        return !currentUser.comedianOnboardingCompleted
    }

    private static func forceComedianOnboardingScreenFromEnvironment() -> Bool {
#if DEBUG
        DebugComedianOnboardingLaunch.shouldForceScreen()
#else
        false
#endif
    }

    @ViewBuilder
    private func appShell(signedOutMessage: String?) -> some View {
        TypedCoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .nearMe:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .nearMe,
                    shellState: shellState,
                    onInitialHomeLoadComplete: markInitialHomeLoaded
                )
            case .search:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .search,
                    shellState: shellState,
                    onInitialHomeLoadComplete: markInitialHomeLoaded
                )
            case .library(let scopedShowIDs):
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .favorites,
                    scopedFavoriteShowIDs: scopedShowIDs,
                    shellState: shellState,
                    onInitialHomeLoadComplete: markInitialHomeLoaded
                )
            case .profile:
                ProfileView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyLocationController: nearbyLocationController,
                    notificationPreferenceStore: serviceContainer.resolve(NotificationPreferenceStore.self),
                    notificationPreferenceSyncClient: serviceContainer.resolveOptional((any NotificationPreferenceSyncing).self),
                    pushTokenManager: serviceContainer.resolveOptional((any PushDeviceTokenManaging).self),
                    profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self),
                    analytics: serviceContainer.resolveOptional(AnalyticsManagerProtocol.self),
                    screenshotPersona: AuthenticatedScreenshotPersona.active
                )
            case .notifications:
                NotificationCenterView(
                    apiClient: apiClient,
                    screenshotItems: AuthenticatedScreenshotPersona.active?.notifications
                )
            case .showDetail(let id):
                ShowDetailView(showID: id, apiClient: apiClient)
            case .comedianDetail(let id):
                ComedianDetailView(comedianID: id, apiClient: apiClient)
            case .clubDetail(let id):
                ClubDetailView(clubId: id, apiClient: apiClient)
            case .podcastDetail(let id):
                PodcastDetailView(podcastID: id, apiClient: apiClient)
            }
        } root: {
            AppShellView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                favorites: favorites,
                shellState: shellState,
                onInitialHomeLoadComplete: markInitialHomeLoaded
            )
        }
        // Mount the persistent podcast mini player on the navigation stack
        // itself, not on AppShellView, so it survives detail-route pushes
        // (showDetail/comedianDetail/clubDetail/podcastDetail replace the
        // shell at the top of the stack). Bottom padding clears the tab
        // bar on the root and the home indicator on pushed details.
        .safeAreaInset(edge: .bottom) {
            PodcastMiniPlayerView(player: podcastPlayer, apiClient: apiClient)
                .padding(.horizontal, theme.spacing.md)
                .padding(.bottom, PodcastMiniPlayerLayout.bottomPadding(
                    theme: theme,
                    clearsRootTabBar: coordinator.routes.isEmpty
                ))
        }
        .environmentObject(favorites)
        .environmentObject(podcastFavorites)
        .environmentObject(podcastPlayer)
        .environmentObject(serviceContainer.resolve(SoftPushPromptCoordinator.self))
        #if DEBUG
        .task {
            guard ProcessInfo.processInfo.environment[UITestLaunchArgs.forceComparisonScreens] == "1",
                  podcastPlayer.currentItem == nil
            else { return }
            podcastPlayer.start(PodcastPlaybackItem(
                id: -1,
                episodeTitle: "The LaughTrack Comedy Roundup",
                podcastName: "LaughTrack",
                podcastImageURL: nil,
                displayRole: "Episode",
                audioURL: nil,
                episodeURL: nil,
                failedAudioURL: nil,
                releaseDate: "Today"
            ))
        }
        .task {
            await DebugSimulatedFavoriteHook.fireIfRequested(
                coordinator: serviceContainer.resolve(SoftPushPromptCoordinator.self)
            )
        }
        #endif
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }

    private func markInitialHomeLoaded() {
        hasLoadedInitialHome = true
    }
}

#if canImport(UIKit)
private struct LaughTrackKeyboardDismissToolbar: ViewModifier {
    func body(content: Content) -> some View {
        content
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") {
                        UIApplication.shared.sendAction(
                            #selector(UIResponder.resignFirstResponder),
                            to: nil,
                            from: nil,
                            for: nil
                        )
                    }
                }
            }
    }
}

private extension View {
    func laughTrackKeyboardDismissToolbar() -> some View {
        modifier(LaughTrackKeyboardDismissToolbar())
    }
}
#else
private extension View {
    func laughTrackKeyboardDismissToolbar() -> some View {
        self
    }
}
#endif

enum PodcastMiniPlayerLayout {
    static let rootTabBarClearance: CGFloat = 68

    static func bottomPadding(theme: AppThemeProtocol, clearsRootTabBar: Bool) -> CGFloat {
        theme.spacing.md +
            (clearsRootTabBar ? rootTabBarClearance : 0)
    }
}

@MainActor
final class FirstEntryAuthChoiceStore: ObservableObject {
    // Storage key kept verbatim for backward compatibility: installs that recorded
    // a guest choice under the old name must keep bypassing the first-entry gate.
    // The flag's meaning has since broadened from "chose guest browsing" to
    // "resolved the first-entry choice (guest OR signed in)".
    static let storageKey = "laughtrack.auth.first-entry-guest-choice"

    @Published private(set) var hasResolvedFirstEntryChoice: Bool

    private let appStateStorage: AppStateStorageProtocol

    init(appStateStorage: AppStateStorageProtocol = AppStateStorage()) {
        self.appStateStorage = appStateStorage
        self.hasResolvedFirstEntryChoice = appStateStorage.getValue(
            forKey: Self.storageKey,
            as: Bool.self
        ) ?? false
    }

    func continueAsGuest() {
        markFirstEntryResolved()
    }

    // Signing in is itself a first-entry choice. Recording it means a later
    // sign-out returns the user to the signed-out shell (.signedOutShell) rather
    // than the full-screen first-launch gate (.authChoiceGate) — the gate exists
    // only for users who have never resolved first entry. Idempotent, so it's safe
    // to call on every .authenticated transition (including session restore on launch,
    // which migrates already-signed-in users from the pre-fix builds).
    func markSignedIn() {
        markFirstEntryResolved()
    }

    private func markFirstEntryResolved() {
        guard !hasResolvedFirstEntryChoice else { return }
        hasResolvedFirstEntryChoice = true
        appStateStorage.setValue(true, forKey: Self.storageKey)
    }
}

private struct FirstEntryAuthChoiceView: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let message: String?
    let logoNamespace: Namespace.ID
    let continueAsGuest: () -> Void
    let signIn: (AuthProvider) -> Void
    @State private var hasAppeared = false

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            laughTrack.colors.canvas
                .ignoresSafeArea()

            LaughTrackSpotlightBackdrop(intensity: 1, lightCenter: UnitPoint(x: 0.5, y: 0.26))
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer(minLength: theme.spacing.lg)

                // The asset carries a 72pt transparent glow margin on every side
                // (see bin/generate-launch-logo.swift), so the frame is sized for
                // a ~156pt visible lockup: 156 × 480/336 ≈ 223.
                Image("LaunchLogo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 223)
                    .matchedGeometryEffect(id: "launch-logo", in: logoNamespace)
                    .shadow(color: laughTrack.colors.accent.opacity(0.42), radius: 38, y: 8)
                    // Reclaim the transparent glow margin (~33pt top and bottom
                    // at this frame size) so layout rhythm tracks the visible
                    // lockup, not the padded bitmap.
                    .padding(.vertical, -24)
                    .entrance(hasAppeared, delay: 0, reduceMotion: reduceMotion)

                MarqueeBulbRow()
                    .padding(.top, theme.spacing.lg)
                    .entrance(hasAppeared, delay: 0.08, reduceMotion: reduceMotion)

                VStack(spacing: theme.spacing.sm) {
                    Text("Live comedy near you")
                        .font(laughTrack.typography.eyebrow)
                        .kerning(3.2)
                        .textCase(.uppercase)
                        .foregroundStyle(laughTrack.colors.accent)

                    (
                        Text("Find your next ")
                            .foregroundColor(laughTrack.colors.textPrimary)
                        + Text("laugh")
                            .foregroundColor(laughTrack.colors.accentStrong)
                    )
                    .font(laughTrack.typography.hero)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)

                    Text(message ?? "Tonight's lineups, hometown clubs, and the comics you follow — all in one place.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.horizontal, theme.spacing.md)
                }
                .padding(.top, theme.spacing.lg)
                .entrance(hasAppeared, delay: 0.14, reduceMotion: reduceMotion)

                Spacer(minLength: theme.spacing.lg)

                VStack(spacing: theme.spacing.sm) {
                    FirstEntryGuestButton {
                        continueAsGuest()
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.firstEntryContinueAsGuestButton)

                    FirstEntrySignInDivider()
                        .padding(.vertical, theme.spacing.xs)

                    ForEach(ContentView.firstEntrySignedOutAuthOptions) { option in
                        SignedOutAuthOptionButton(option: option, action: signIn)
                            .accessibilityIdentifier(LaughTrackViewTestID.firstEntryAuthOptionButton(option.provider))
                    }
                }
                .entrance(hasAppeared, delay: 0.22, reduceMotion: reduceMotion)
                .padding(.bottom, theme.spacing.lg)
            }
            .padding(.horizontal, theme.spacing.xl)
            .frame(maxWidth: 520)
        }
        .onAppear {
            hasAppeared = true
        }
    }
}

private extension View {
    /// Staggered entrance used by the first-entry gate: fade + rise, with a
    /// per-element delay. Collapses to an instant cut under Reduce Motion.
    func entrance(_ hasAppeared: Bool, delay: Double, reduceMotion: Bool) -> some View {
        self
            .opacity(hasAppeared ? 1 : 0)
            .offset(y: hasAppeared || reduceMotion ? 0 : 14)
            .animation(
                reduceMotion
                    ? .easeOut(duration: 0.1)
                    : .spring(response: 0.5, dampingFraction: 0.86).delay(0.08 + delay),
                value: hasAppeared
            )
    }
}

/// A short run of marquee bulbs — the club-sign detail that separates the
/// brand mark from the headline. Purely decorative.
private struct MarqueeBulbRow: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: 12) {
            ForEach(0..<5, id: \.self) { index in
                let distanceFromCenter = abs(index - 2)
                Circle()
                    .fill(laughTrack.colors.accentStrong.opacity(1.0 - Double(distanceFromCenter) * 0.3))
                    .frame(width: index == 2 ? 6 : 4.5, height: index == 2 ? 6 : 4.5)
                    .shadow(
                        color: laughTrack.colors.accentStrong.opacity(0.8 - Double(distanceFromCenter) * 0.25),
                        radius: 5
                    )
            }
        }
        .accessibilityHidden(true)
    }
}

private struct FirstEntrySignInDivider: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.sm) {
            dividerLine(fadingToward: .leading)
            Text("or sign in to sync favorites & alerts")
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .lineLimit(1)
                .minimumScaleFactor(0.85)
                .layoutPriority(1)
            dividerLine(fadingToward: .trailing)
        }
    }

    private func dividerLine(fadingToward edge: UnitPoint) -> some View {
        LinearGradient(
            colors: [theme.laughTrackTokens.colors.borderStrong, .clear],
            startPoint: edge == .leading ? .trailing : .leading,
            endPoint: edge
        )
        .frame(height: 1)
    }
}

private struct FirstEntryGuestButton: View {
    @Environment(\.appTheme) private var theme

    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            HStack(spacing: theme.spacing.sm) {
                Text("Continue as guest")
                    .font(laughTrack.typography.action)
                    .lineLimit(1)
                    .minimumScaleFactor(0.9)

                Image(systemName: "arrow.right")
                    .font(.system(size: 17, weight: .semibold))
            }
            .foregroundStyle(laughTrack.colors.textInverse)
            .frame(maxWidth: .infinity, minHeight: 54)
            .padding(.horizontal, theme.spacing.md)
            .contentShape(Rectangle())
            .background(
                LinearGradient(
                    colors: [laughTrack.colors.accentStrong, laughTrack.colors.accent],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
                    .strokeBorder(
                        LinearGradient(
                            colors: [Color.white.opacity(0.35), .clear],
                            startPoint: .top,
                            endPoint: .bottom
                        ),
                        lineWidth: 1
                    )
            )
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
            .shadow(color: laughTrack.colors.accent.opacity(0.38), radius: 18, y: 8)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Continue as guest")
    }
}
