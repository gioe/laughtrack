import SwiftUI
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

enum LaughTrackViewTestID {
    static let homeScreen = "laughtrack.home.screen"
    static let searchTabScreen = "laughtrack.search-tab.screen"
    static let activityTabScreen = "laughtrack.activity-tab.screen"
    static let profileTabScreen = "laughtrack.profile-tab.screen"
    static let homeSettingsButton = "laughtrack.home.settings-button"
    static let homeShowsSearchButton = "laughtrack.home.shows-search-button"
    static let homeClubsSearchButton = "laughtrack.home.clubs-search-button"
    static let homeComediansSearchButton = "laughtrack.home.comedians-search-button"
    static let settingsScreen = "laughtrack.settings.screen"
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
    static let settingsFavoritesSection = "laughtrack.settings.favorites-section"

    static func showsSearchResultButton(_ id: Int) -> String {
        "laughtrack.shows-search.result-\(id)"
    }

    static func comediansSearchResultButton(_ id: Int) -> String {
        "laughtrack.comedians-search.result-\(id)"
    }

    static func clubsSearchResultButton(_ id: Int) -> String {
        "laughtrack.clubs-search.result-\(id)"
    }
}

struct ContentView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var favorites = ComedianFavoriteStore()

    var body: some View {
        Group {
            switch authManager.state {
            case .restoring:
                AuthLoadingView(message: "Restoring your LaughTrack session…")
            case .signingIn(let provider):
                AuthLoadingView(message: "Finishing \(provider.displayName) sign-in…")
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
    }

    @ViewBuilder
    private func appShell(signedOutMessage: String?) -> some View {
        CoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .home:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .home
                )
            case .search:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .search
                )
            case .activity:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .activity
                )
            case .profile:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .profile
                )
            case .settings:
                SettingsView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self)
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
                favorites: favorites
            )
        }
        .environmentObject(favorites)
    }
}

struct SettingsView: View {
    let apiClient: Client
    let signedOutMessage: String?
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @StateObject private var model: SettingsNearbyPreferenceModel

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyPreferenceStore: NearbyPreferenceStore,
        model: SettingsNearbyPreferenceModel? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.nearbyPreferenceStore = nearbyPreferenceStore
        let resolvedModel = model ?? SettingsNearbyPreferenceModel(
            nearbyPreferenceStore: nearbyPreferenceStore
        )
        _model = StateObject(
            wrappedValue: resolvedModel
        )
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Settings",
                    title: "Real preferences, not placeholder toggles",
                    subtitle: "Save the nearby filters LaughTrack actually uses today, keep account state truthful, and avoid controls the app cannot honor yet."
                )

                if let signedOutMessage {
                    LaughTrackAuthMessageCard(message: signedOutMessage)
                }

                nearbyPreferencesSection

                notificationsSection

                if let session = authManager.currentSession {
                    LaughTrackSectionHeader(
                        eyebrow: "Account",
                        title: "Signed in on this device",
                        subtitle: "Account status stays accurate to the saved mobile session."
                    )

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                            Text(session.provider?.displayName ?? "Saved session")
                                .font(laughTrack.typography.cardTitle)
                                .foregroundStyle(laughTrack.colors.textPrimary)
                            Text(
                                session.expiresAt.map {
                                    "Session expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                                } ?? "Session expiration is not available."
                            )
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)

                            LaughTrackButton(
                                "Sign out",
                                systemImage: "rectangle.portrait.and.arrow.right",
                                tone: .destructive
                            ) {
                                Task {
                                    await authManager.signOut()
                                }
                            }
                        }
                    }

                    SavedFavoritesSection(apiClient: apiClient)
                } else {
                    LaughTrackSectionHeader(
                        eyebrow: "Sign in",
                        title: "Save favorites across sessions",
                        subtitle: "Sign in when you want synced favorite comedians and recovery messaging tied to a real account."
                    )

                    LaughTrackCard(tone: .accent) {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                            Text("LaughTrack account")
                                .font(laughTrack.typography.eyebrow)
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                                .textCase(.uppercase)
                            Text("Keep your account state in sync.")
                                .font(laughTrack.typography.screenTitle)
                                .foregroundStyle(laughTrack.colors.textInverse)
                            Text("Signing in lets LaughTrack keep favorite comedians with your account instead of only on this device.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                        }
                    }

                    VStack(spacing: laughTrack.spacing.itemGap) {
                        ForEach(AuthProvider.allCases, id: \.self) { provider in
                            LaughTrackAuthProviderCard(provider: provider) {
                                Task {
                                    await authManager.signIn(with: provider)
                                }
                            }
                        }
                    }

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                            Text("What this enables")
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.accent)
                                .textCase(.uppercase)
                            Text("A signed-in session lets the app keep favorite-comedian actions tied to your account and recover cleanly if sign-in is interrupted.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        }
                    }
                }
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, laughTrack.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.settingsScreen)
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .navigationTitle("Settings")
        .task(id: authManager.currentSession == nil) {
            if authManager.currentSession == nil {
                favorites.resetSavedFavorites()
            } else {
                await favorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager
                )
            }
        }
    }

    private var nearbyPreferencesSection: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Browse",
                title: "Nearby defaults",
                subtitle: "Home and nearby results read from the same saved ZIP code and radius."
            )

            if let preference = model.nearbyPreference {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        Text("Nearby preference saved")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(
                            preference.source == .manual
                                ? "LaughTrack is using your saved manual nearby preference."
                                : "LaughTrack last saved a nearby preference from your current location."
                        )
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)

                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackBadge("ZIP \(preference.zipCode)", systemImage: "mappin.and.ellipse", tone: .neutral)
                            LaughTrackBadge("\(preference.distanceMiles) mi", systemImage: "location.fill", tone: .highlight)
                            LaughTrackBadge(
                                preference.source == .manual ? "Saved manually" : "Saved from location",
                                systemImage: preference.source == .manual ? "slider.horizontal.3" : "location.north.line",
                                tone: .accent
                            )
                        }
                    }
                }
                .accessibilityIdentifier(LaughTrackViewTestID.settingsNearbySavedState)
            } else {
                LaughTrackStateView(
                    tone: .empty,
                    title: "No nearby preference saved",
                    message: "Save a ZIP code and distance here to reuse the same nearby defaults on home and nearby search."
                )
                .accessibilityIdentifier(LaughTrackViewTestID.settingsNearbyEmptyState)
            }

            LaughTrackCard(tone: .muted) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Edit nearby preference")
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text("The saved ZIP code and distance below are persisted on this device and used by the nearby sections.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)

                    settingsTextField(
                        title: "Saved ZIP code",
                        text: $model.zipCodeDraft
                    )
                        .accessibilityLabel("Saved ZIP code")
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsZipField)

                    VStack(alignment: .leading, spacing: theme.spacing.sm) {
                        Text("Distance")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)

                        Picker("Distance", selection: $model.distanceMiles) {
                            ForEach(SettingsNearbyPreferenceModel.distanceOptions, id: \.self) { distance in
                                Text("\(distance) mi").tag(distance)
                            }
                        }
                        .pickerStyle(.segmented)
                        .accessibilityLabel("Distance")
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsDistancePicker)
                    }

                    if let validationMessage = model.validationMessage {
                        Text(validationMessage)
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.danger)
                    }

                    VStack(spacing: theme.spacing.sm) {
                        LaughTrackButton(
                            "Save nearby preference",
                            systemImage: "square.and.arrow.down"
                        ) {
                            model.saveNearbyPreference()
                        }
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsSaveButton)

                        if model.nearbyPreference != nil {
                            LaughTrackButton(
                                "Clear nearby preference",
                                systemImage: "trash",
                                tone: .destructive
                            ) {
                                model.clearNearbyPreference()
                            }
                            .accessibilityIdentifier(LaughTrackViewTestID.settingsClearButton)
                        }
                    }
                }
            }
        }
    }

    private var notificationsSection: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Notifications",
                title: "No fake alert toggles",
                subtitle: "Push settings only belong here once the iOS app can actually honor them."
            )

            LaughTrackStateView(
                tone: .empty,
                title: "Push notifications are not available yet",
                message: "This build does not deliver push alerts, so Settings intentionally avoids notification switches that would imply working behavior."
            )
        }
    }

    private func settingsTextField(
        title: String,
        text: Binding<String>
    ) -> some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text(title)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)

            TextField(title, text: text)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .padding(.horizontal, theme.spacing.md)
                .padding(.vertical, theme.spacing.md)
                .background(laughTrack.colors.surfaceElevated)
                .overlay(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        }
    }
}

private struct SavedFavoritesSection: View {
    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Favorites",
                title: "Saved comedians",
                subtitle: "Comedians you've saved."
            )

            LaughTrackCard {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    switch favorites.savedFavoritesPhase {
                    case .idle, .loading:
                        LaughTrackStateView(
                            tone: .loading,
                            title: "Loading saved favorites",
                            message: "LaughTrack is fetching your saved comedians from your account."
                        )
                    case .empty:
                        LaughTrackStateView(
                            tone: .empty,
                            title: "No saved favorites yet",
                            message: "Favorite a comedian anywhere in LaughTrack and it will appear here for this account."
                        )
                    case .failure(let message):
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                            LaughTrackStateView(
                                tone: .error,
                                title: "Couldn’t load saved favorites",
                                message: message
                            )
                            LaughTrackButton(
                                "Retry favorites",
                                systemImage: "arrow.clockwise"
                            ) {
                                Task {
                                    await favorites.loadSavedFavorites(
                                        apiClient: apiClient,
                                        authManager: authManager,
                                        force: true
                                    )
                                }
                            }
                        }
                    case .loaded:
                        ForEach(favorites.savedFavoriteComedians, id: \.uuid) { comedian in
                            Button {
                                coordinator.push(.comedianDetail(comedian.id))
                            } label: {
                                HStack(spacing: laughTrack.spacing.itemGap) {
                                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                                        Text(comedian.name)
                                            .font(laughTrack.typography.cardTitle)
                                            .foregroundStyle(laughTrack.colors.textPrimary)
                                        Text(
                                            comedian.showCount == 1
                                                ? "1 tracked show appearance"
                                                : "\(comedian.showCount) tracked show appearances"
                                        )
                                        .font(laughTrack.typography.body)
                                        .foregroundStyle(laughTrack.colors.textSecondary)
                                    }

                                    Spacer()

                                    Image(systemName: "chevron.right")
                                        .foregroundStyle(laughTrack.colors.textSecondary)
                                }
                                .padding(.vertical, laughTrack.spacing.tight)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.settingsFavoritesSection)
    }
}

private struct AuthLoadingView: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: laughTrack.spacing.sectionGap) {
            LaughTrackCard(tone: .accent) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("LaughTrack account")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                        .textCase(.uppercase)
                    Text("Signing you in with the shared token flow.")
                        .font(laughTrack.typography.screenTitle)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("The browser handoff and session exchange stay the same; this screen now uses the same branded cards and typography as the rest of the app.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }
            }

            LaughTrackStateView(
                tone: .loading,
                title: "Loading LaughTrack",
                message: message
            )
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
    }
}

struct LaughTrackNavigationChrome: ViewModifier {
    let background: Color

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .toolbarBackground(background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        #else
        content
        #endif
    }
}
