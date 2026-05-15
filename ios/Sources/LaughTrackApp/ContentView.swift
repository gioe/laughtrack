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
    enum RootSurface: Equatable {
        case loading
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

    var body: some View {
        Group {
            switch Self.rootSurface(
                authState: authManager.state,
                hasLoadedCurrentUser: authManager.hasLoadedCurrentUser,
                currentUser: authManager.currentUser
            ) {
            case .loading:
                AuthLoadingView()
            case .signedOutShell(let message):
                appShell(signedOutMessage: message)
            case .comedianOnboarding:
                ComedianOnboardingView(
                    apiClient: apiClient,
                    favorites: favorites,
                    notificationPreferenceStore: serviceContainer.resolve(NotificationPreferenceStore.self),
                    notificationPreferenceSyncClient: serviceContainer.resolveOptional((any NotificationPreferenceSyncing).self)
                )
                .environmentObject(favorites)
            case .authenticatedShell:
                appShell(signedOutMessage: nil)
            }
        }
        .tint(theme.colors.primary)
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
        currentUser: AuthenticatedUser?
    ) -> RootSurface {
        switch authState {
        case .restoring, .signingIn:
            return .loading
        case .signedOut(let message):
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
