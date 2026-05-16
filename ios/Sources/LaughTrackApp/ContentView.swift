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
    static let locationHeaderButton = "laughtrack.location.header-button"
    static let locationPermissionPitch = "laughtrack.location-permission.pitch"
    static let locationPermissionAllowButton = "laughtrack.location-permission.allow-button"
    static let locationPermissionManualZipButton = "laughtrack.location-permission.manual-zip-button"
    static let locationPermissionCloseButton = "laughtrack.location-permission.close-button"
    static let homeSettingsButton = "laughtrack.home.settings-button"
    static let homeShowsSearchButton = "laughtrack.home.shows-search-button"
    static let homeClubsSearchButton = "laughtrack.home.clubs-search-button"
    static let homeComediansSearchButton = "laughtrack.home.comedians-search-button"
    static let homeNearMeHeader = "laughtrack.home.near-me-header"
    static let homeShowsTonightRail = "laughtrack.home.shows-tonight-rail"
    static let homeShowsTonightHeroButton = "laughtrack.home.shows-tonight-hero-button"
    static let homeShowsTonightSeeMoreButton = "laughtrack.home.shows-tonight-see-more-button"
    static let homeTrendingComediansRail = "laughtrack.home.trending-comedians-rail"
    static let homeFavoriteShowsRail = "laughtrack.home.favorite-shows-rail"
    static let homePopularClubsRail = "laughtrack.home.popular-clubs-rail"
    static let showsSearchScreen = "laughtrack.shows-search.screen"
    static let clubsSearchScreen = "laughtrack.clubs-search.screen"
    static let comediansSearchScreen = "laughtrack.comedians-search.screen"
    static let showDetailScreen = "laughtrack.show-detail.screen"
    static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
    static let comedianDetailTabPicker = "laughtrack.comedian-detail.tab-picker"
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

struct HomeLocationFilterModal: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var nearbyLocationController: NearbyLocationController
    @Binding var isPresented: Bool
    @State private var zipCodeDraft = ""

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text("Location")
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text("Set the location used for nearby home results.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }

                Spacer(minLength: 0)

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: theme.iconSizes.sm, weight: .bold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                        .background(laughTrack.colors.surfaceElevated)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close")
            }

            LaughTrackSearchField(placeholder: "10012", text: $zipCodeDraft) {
                Button {
                    applyZip()
                } label: {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.accent)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Apply ZIP")
            }
            .modifier(SearchFieldInputBehavior())
            #if os(iOS)
            .keyboardType(UIKeyboardType.numberPad)
            #endif
            .onSubmit(applyZip)

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton("Apply", systemImage: "checkmark", density: .compact) {
                    applyZip()
                }

                LaughTrackButton(
                    nearbyLocationController.isResolvingCurrentLocation ? "Finding ZIP..." : "Current location",
                    systemImage: "location.fill",
                    tone: .secondary,
                    density: .compact
                ) {
                    Task {
                        let didResolve = await nearbyLocationController.useCurrentLocation(
                            distanceMiles: nearbyLocationController.preference?.distanceMiles
                                ?? NearbyPreference.defaultDistanceMiles
                        )
                        if didResolve {
                            isPresented = false
                        }
                    }
                }
                .disabled(nearbyLocationController.isResolvingCurrentLocation)

                if nearbyLocationController.preference != nil {
                    LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact) {
                        nearbyLocationController.clear()
                        isPresented = false
                    }
                }
            }

            if let statusMessage = nearbyLocationController.statusMessage {
                InlineStatusMessage(message: statusMessage)

                if statusMessage == NearbyLocationError.denied.recoveryMessage {
                    LaughTrackButton("Open Settings", systemImage: "gearshape", tone: .secondary, density: .compact, fullWidth: false) {
                        openAppSettings()
                    }
                }
            }

            Spacer(minLength: 0)
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .onAppear {
            zipCodeDraft = nearbyLocationController.preference?.zipCode ?? ""
        }
    }

    private func applyZip() {
        let distanceMiles = nearbyLocationController.preference?.distanceMiles
            ?? NearbyPreference.defaultDistanceMiles
        if nearbyLocationController.applyManualZip(zipCodeDraft, distanceMiles: distanceMiles) {
            isPresented = false
        }
    }

    private func openAppSettings() {
        #if canImport(UIKit)
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
        #endif
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
    @StateObject private var shellState = AppShellState()
    @StateObject private var firstEntryAuthChoiceStore = FirstEntryAuthChoiceStore()
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
        case .restoring, .signingIn:
            return .loading
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
                ClubDetailView(clubID: id, apiClient: apiClient)
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
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
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
                        Text("Pick up where you left off")
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
