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
    static let homeTrendingComediansRail = "laughtrack.home.trending-comedians-rail"
    static let homeFavoriteShowsRail = "laughtrack.home.favorite-shows-rail"
    static let homePopularClubsRail = "laughtrack.home.popular-clubs-rail"
    static let showsSearchScreen = "laughtrack.shows-search.screen"
    static let clubsSearchScreen = "laughtrack.clubs-search.screen"
    static let comediansSearchScreen = "laughtrack.comedians-search.screen"
    static let showDetailScreen = "laughtrack.show-detail.screen"
    static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
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

private struct HomeLocationFilterModal: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var nearbyLocationController: NearbyLocationController
    @Binding var isPresented: Bool
    @State private var zipCodeDraft = ""

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            Color.black.opacity(0.28)
                .ignoresSafeArea()
                .onTapGesture {
                    isPresented = false
                }

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
            }
            .padding(theme.spacing.xl)
            .background(laughTrack.colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
            .shadowStyle(laughTrack.shadows.floating)
            .padding(.horizontal, theme.spacing.xl)
        }
        .background(.clear)
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
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var favorites = ComedianFavoriteStore()
    @StateObject private var shellState = AppShellState()
    @State private var isHomeLocationEditorPresented = false

    var body: some View {
        Group {
            switch authManager.state {
            case .restoring, .signingIn:
                AuthLoadingView()
            case .signedOut(let message):
                appShell(signedOutMessage: message)
            case .authenticated:
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
                    nearbyLocationController: nearbyLocationController
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
        .overlay(alignment: .topLeading) {
            if coordinator.path.isEmpty {
                accountHeader
                    .padding(.leading, theme.spacing.lg)
                    .padding(.top, AccountHeaderLayout.accountHeaderTopPadding(
                        safeAreaTop: currentTopSafeAreaInset,
                        theme: theme
                    ))
                    .ignoresSafeArea(.container, edges: .top)
            }
        }
        .overlay(alignment: .topTrailing) {
            if coordinator.path.isEmpty && shellState.selectedTab == .nearMe {
                locationHeaderButton
                    .padding(.trailing, theme.spacing.lg)
                    .padding(.top, AccountHeaderLayout.accountHeaderTopPadding(
                        safeAreaTop: currentTopSafeAreaInset,
                        theme: theme
                    ))
                    .ignoresSafeArea(.container, edges: .top)
            }
        }
        .sheet(isPresented: $shellState.isLocationPermissionPitchPresented) {
            LocationPermissionPitchView(
                nearbyLocationController: nearbyLocationController,
                onResolved: {
                    shellState.dismissLocationPermissionPitch()
                },
                onManualZip: {
                    shellState.dismissLocationPermissionPitchForManualZip()
                    coordinator.push(.profile)
                },
                onClose: {
                    shellState.dismissLocationPermissionPitch()
                }
            )
            .environment(\.appTheme, theme)
        }
        #if os(iOS)
        .fadeFullScreenCover(isPresented: $isHomeLocationEditorPresented) {
            HomeLocationFilterModal(
                nearbyLocationController: nearbyLocationController,
                isPresented: $isHomeLocationEditorPresented
            )
            .environment(\.appTheme, theme)
        }
        #else
        .sheet(isPresented: $isHomeLocationEditorPresented) {
            HomeLocationFilterModal(
                nearbyLocationController: nearbyLocationController,
                isPresented: $isHomeLocationEditorPresented
            )
            .environment(\.appTheme, theme)
        }
        #endif
    }

    private var accountHeader: some View {
        HStack(spacing: theme.spacing.sm) {
            accountHeaderButton

            primitiveFilterRow
        }
    }

    private var accountHeaderButton: some View {
        shellHeaderIconButton(
            systemImage: "person.crop.circle",
            accessibilityLabel: "Account",
            accessibilityIdentifier: LaughTrackViewTestID.accountHeaderButton
        ) {
            coordinator.push(AppRoute.accountHeaderTarget())
        }
    }

    private var locationHeaderButton: some View {
        shellHeaderIconButton(
            systemImage: "location.fill",
            accessibilityLabel: "Location",
            accessibilityIdentifier: LaughTrackViewTestID.locationHeaderButton
        ) {
            isHomeLocationEditorPresented = true
        }
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }

    private func shellHeaderIconButton(
        systemImage: String,
        accessibilityLabel: String,
        accessibilityIdentifier: String,
        action: @escaping () -> Void
    ) -> some View {
        let tokens = theme.laughTrackTokens

        return Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 32, weight: .semibold))
                .foregroundStyle(tokens.colors.textPrimary)
                .frame(width: AccountHeaderLayout.buttonSize, height: AccountHeaderLayout.buttonSize)
                .background {
                    Circle()
                        .fill(tokens.colors.surfaceElevated.opacity(0.94))
                        .shadow(color: .black.opacity(0.08), radius: 12, x: 0, y: 6)
                }
                .overlay {
                    Circle()
                        .stroke(tokens.colors.borderSubtle, lineWidth: 1)
                }
        }
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier(accessibilityIdentifier)
    }

    private var primitiveFilterRow: some View {
        HStack(spacing: theme.spacing.xs) {
            ForEach(SearchRootModel.Pivot.allCases) { primitive in
                Button {
                    shellState.selectPrimitive(primitive)
                } label: {
                    Text(primitive.title)
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(primitive == shellState.selectedPrimitive ? theme.laughTrackTokens.colors.textInverse : theme.laughTrackTokens.colors.textPrimary)
                        .padding(.horizontal, 12)
                        .frame(height: 34)
                        .background {
                            Capsule()
                                .fill(primitive == shellState.selectedPrimitive ? theme.laughTrackTokens.colors.accentStrong : theme.laughTrackTokens.colors.surfaceElevated.opacity(0.94))
                                .shadow(color: .black.opacity(0.08), radius: 10, x: 0, y: 5)
                        }
                        .overlay {
                            Capsule()
                                .stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel(primitive.title)
                .accessibilityIdentifier(LaughTrackViewTestID.primitiveFilterButton(primitive.rawValue))
            }
        }
    }

    private var currentTopSafeAreaInset: CGFloat {
        #if canImport(UIKit)
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first { $0.isKeyWindow }?
            .safeAreaInsets.top ?? 0
        #else
        0
        #endif
    }
}
