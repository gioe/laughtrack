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
    static let accountHeaderButton = "laughtrack.account.header-button"
    static let locationPermissionPitch = "laughtrack.location-permission.pitch"
    static let locationPermissionAllowButton = "laughtrack.location-permission.allow-button"
    static let locationPermissionManualZipButton = "laughtrack.location-permission.manual-zip-button"
    static let locationPermissionCloseButton = "laughtrack.location-permission.close-button"
    static let homeSettingsButton = "laughtrack.home.settings-button"
    static let homeShowsSearchButton = "laughtrack.home.shows-search-button"
    static let homeClubsSearchButton = "laughtrack.home.clubs-search-button"
    static let homeComediansSearchButton = "laughtrack.home.comedians-search-button"
    static let homeDiscoverHeader = "laughtrack.home.discover-header"
    static let homeShowsTonightRail = "laughtrack.home.shows-tonight-rail"
    static let homeShowsTonightHeroButton = "laughtrack.home.shows-tonight-hero-button"
    static let homeShowsTonightSeeMoreButton = "laughtrack.home.shows-tonight-see-more-button"
    static let homeTrendingComediansRail = "laughtrack.home.trending-comedians-rail"
    static let homeFavoriteShowsRail = "laughtrack.home.favorite-shows-rail"
    static let homePopularClubsRail = "laughtrack.home.popular-clubs-rail"
    static let homeTrendingPodcastsRail = "laughtrack.home.trending-podcasts-rail"
    static let showsSearchScreen = "laughtrack.shows-search.screen"
    static let clubsSearchScreen = "laughtrack.clubs-search.screen"
    static let comediansSearchScreen = "laughtrack.comedians-search.screen"
    static let showDetailScreen = "laughtrack.show-detail.screen"
    static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
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

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var favorites = ComedianFavoriteStore()
    @StateObject private var podcastFavorites = PodcastFavoriteStore()
    @StateObject private var shellState = AppShellState()
    @StateObject private var firstEntryAuthChoiceStore = FirstEntryAuthChoiceStore()
    @StateObject private var podcastPlayer = PodcastPlaybackController()
    @Namespace private var authLogoNamespace

    var body: some View {
        let surface = Self.rootSurface(
            authState: authManager.state,
            hasLoadedCurrentUser: authManager.hasLoadedCurrentUser,
            currentUser: authManager.currentUser,
            hasChosenGuestBrowsing: firstEntryAuthChoiceStore.hasChosenGuestBrowsing
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
                    favorites: favorites,
                    notificationPreferenceStore: serviceContainer.resolve(NotificationPreferenceStore.self),
                    notificationPreferenceSyncClient: serviceContainer.resolveOptional((any NotificationPreferenceSyncing).self)
                )
                .environmentObject(favorites)
                .transition(.opacity)
            case .authenticatedShell:
                appShell(signedOutMessage: nil)
                    .transition(.opacity)
            }
        }
        .tint(theme.colors.primary)
        .animation(.easeInOut(duration: 0.42), value: surface)
        .task {
            await authManager.restoreSessionIfNeeded()
        }
        .onReceive(authManager.$state) { state in
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
        hasChosenGuestBrowsing: Bool = false
    ) -> RootSurface {
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
            guard hasChosenGuestBrowsing else {
                return .loading
            }
            return .signedOutShell(message: nil)
        case .signedOut(let message):
            guard hasChosenGuestBrowsing else {
                return .authChoiceGate(message: message)
            }

            return .signedOutShell(message: message)
        case .authenticated:
            guard hasLoadedCurrentUser else {
                return .loading
            }

            if shouldPresentComedianOnboarding(authState: authState, currentUser: currentUser) {
                return .comedianOnboarding
            }

            return .authenticatedShell
        }
    }

    static func shouldPresentComedianOnboarding(
        authState: AuthManager.State,
        currentUser: AuthenticatedUser?
    ) -> Bool {
        guard case .authenticated = authState,
              let currentUser
        else { return false }

        return !currentUser.comedianOnboardingCompleted
    }

    @ViewBuilder
    private func appShell(signedOutMessage: String?) -> some View {
        CoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .nearMe:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .nearMe,
                    shellState: shellState
                )
            case .search:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .search,
                    shellState: shellState
                )
            case .library:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .favorites,
                    shellState: shellState
                )
            case .profile:
                ProfileView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyLocationController: nearbyLocationController,
                    notificationPreferenceStore: serviceContainer.resolve(NotificationPreferenceStore.self),
                    notificationPreferenceSyncClient: serviceContainer.resolveOptional((any NotificationPreferenceSyncing).self),
                    profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self)
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
                shellState: shellState
            )
        }
        .environmentObject(favorites)
        .environmentObject(podcastFavorites)
        .environmentObject(podcastPlayer)
        .safeAreaInset(edge: .bottom) {
            PodcastMiniPlayerView(player: podcastPlayer, apiClient: apiClient)
                .padding(.horizontal, theme.spacing.md)
                .padding(.bottom, theme.spacing.sm)
        }
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }
}

private struct PodcastMiniPlayerView: View {
    @ObservedObject var player: PodcastPlaybackController
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @State private var isExpanded = false
    @State private var dragOffset: CGFloat = 0

    private static let dismissThreshold: CGFloat = 60

    var body: some View {
        if let item = player.currentItem {
            content(item: item)
                .offset(y: dragOffset)
                .gesture(dismissGesture)
                .sheet(isPresented: $isExpanded) {
                    NowPlayingView(player: player, apiClient: apiClient)
                        .presentationDetents([.large])
                }
        }
    }

    @ViewBuilder
    private func content(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: expand) {
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    artwork(item: item)
                        .frame(width: 44, height: 44)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))

                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.episodeTitle)
                            .font(laughTrack.typography.body.weight(.semibold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(1)

                        Text(item.podcastName)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    transportCluster(item: item)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)

                progressBar
            }
        }
        .buttonStyle(.plain)
        .frame(maxWidth: .infinity)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.floating)
        .accessibilityIdentifier(LaughTrackViewTestID.podcastMiniPlayer)
    }

    @ViewBuilder
    private func transportCluster(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens

        if item.requiresExternalFallback {
            if let episodeURL = item.episodeURL {
                Button {
                    openURL(episodeURL)
                } label: {
                    Image(systemName: "arrow.up.right.square")
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 38, height: 38)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open episode")
            }
        } else {
            HStack(spacing: 6) {
                Button {
                    player.skipBack()
                } label: {
                    Image(systemName: "gobackward.15")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Skip back 15 seconds")

                Button {
                    player.togglePlayPause()
                } label: {
                    Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                        .font(.system(size: theme.iconSizes.md, weight: .bold))
                        .foregroundStyle(laughTrack.colors.textInverse)
                        .frame(width: 38, height: 38)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(player.isPlaying ? "Pause podcast" : "Play podcast")

                Button {
                    player.skipForward()
                } label: {
                    Image(systemName: "goforward.30")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Skip forward 30 seconds")
            }
        }
    }

    @ViewBuilder
    private func artwork(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens
        let raw = item.podcastImageURL?.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolved = (raw?.isEmpty ?? true) ? nil : raw

        if let raw = resolved, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                fallbackArtwork
            } error: { _ in
                fallbackArtwork
            }
        } else if item.requiresExternalFallback {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
                .overlay {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.warning)
                }
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens
        return RoundedRectangle(cornerRadius: 8, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private var progressBar: some View {
        let laughTrack = theme.laughTrackTokens
        let duration = player.duration
        let fraction = duration > 0 ? min(1, max(0, player.currentTime / duration)) : 0

        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(laughTrack.colors.borderSubtle.opacity(0.5))
                Rectangle()
                    .fill(laughTrack.colors.accent)
                    .frame(width: proxy.size.width * fraction)
            }
        }
        .frame(height: 2)
    }

    private var dismissGesture: some Gesture {
        DragGesture()
            .onChanged { value in
                guard value.translation.height > 0 else { return }
                dragOffset = value.translation.height
            }
            .onEnded { value in
                if value.translation.height > Self.dismissThreshold {
                    withAnimation(.easeIn(duration: 0.18)) {
                        dragOffset = 240
                    }
                    Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 180_000_000)
                        dragOffset = 0
                        player.dismiss()
                    }
                } else {
                    withAnimation(.spring(response: 0.32, dampingFraction: 0.85)) {
                        dragOffset = 0
                    }
                }
            }
    }

    private func expand() {
        isExpanded = true
    }
}

@MainActor
final class FirstEntryAuthChoiceStore: ObservableObject {
    static let storageKey = "laughtrack.auth.first-entry-guest-choice"

    @Published private(set) var hasChosenGuestBrowsing: Bool

    private let appStateStorage: AppStateStorageProtocol

    init(appStateStorage: AppStateStorageProtocol = AppStateStorage()) {
        self.appStateStorage = appStateStorage
        self.hasChosenGuestBrowsing = appStateStorage.getValue(
            forKey: Self.storageKey,
            as: Bool.self
        ) ?? false
    }

    func continueAsGuest() {
        hasChosenGuestBrowsing = true
        appStateStorage.setValue(true, forKey: Self.storageKey)
    }
}

private struct FirstEntryAuthChoiceView: View {
    @Environment(\.appTheme) private var theme

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

            VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
                Spacer(minLength: theme.spacing.xl)

                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Image("LaunchLogo")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 144, height: 144)
                        .matchedGeometryEffect(id: "launch-logo", in: logoNamespace)
                        .padding(.bottom, theme.spacing.xs)

                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text("Find your next laugh")
                            .font(laughTrack.typography.screenTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text(message ?? "Browse tonight's shows as a guest, or sign in to sync favorites and alerts.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .opacity(hasAppeared ? 1 : 0)
                .offset(y: hasAppeared ? 0 : 10)

                VStack(spacing: theme.spacing.sm) {
                    FirstEntryGuestButton {
                        continueAsGuest()
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.firstEntryContinueAsGuestButton)

                    ForEach(ContentView.firstEntrySignedOutAuthOptions) { option in
                        SignedOutAuthOptionButton(option: option, action: signIn)
                            .accessibilityIdentifier(LaughTrackViewTestID.firstEntryAuthOptionButton(option.provider))
                    }
                }
                .opacity(hasAppeared ? 1 : 0)
                .offset(y: hasAppeared ? 0 : 16)

                Spacer(minLength: theme.spacing.xl)
            }
            .padding(.horizontal, theme.spacing.xl)
            .frame(maxWidth: 520, alignment: .leading)
        }
        .onAppear {
            withAnimation(.spring(response: 0.48, dampingFraction: 0.86).delay(0.08)) {
                hasAppeared = true
            }
        }
    }
}

private struct FirstEntryGuestButton: View {
    @Environment(\.appTheme) private var theme

    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            HStack(spacing: theme.spacing.sm) {
                Image(systemName: "arrow.right")
                    .font(.system(size: 21, weight: .semibold))
                    .frame(width: 24)

                Text("Continue as guest")
                    .font(laughTrack.typography.action)
                    .lineLimit(1)
                    .minimumScaleFactor(0.9)
            }
            .foregroundStyle(laughTrack.colors.textInverse)
            .frame(maxWidth: .infinity, minHeight: 44)
            .padding(.horizontal, theme.spacing.md)
            .contentShape(Rectangle())
            .background(laughTrack.colors.accent)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Continue as guest")
    }
}
