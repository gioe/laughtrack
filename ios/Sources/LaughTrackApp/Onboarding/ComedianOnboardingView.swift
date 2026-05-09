import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComedianOnboardingView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let notificationPreferenceStore: NotificationPreferenceStore
    let notificationPreferenceSyncClient: (any NotificationPreferenceSyncing)?

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var authManager: AuthManager
    @StateObject private var model: ComedianOnboardingModel

    @MainActor
    init(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        notificationPreferenceStore: NotificationPreferenceStore,
        notificationPreferenceSyncClient: (any NotificationPreferenceSyncing)?,
        model: ComedianOnboardingModel? = nil
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.notificationPreferenceStore = notificationPreferenceStore
        self.notificationPreferenceSyncClient = notificationPreferenceSyncClient
        _model = StateObject(wrappedValue: model ?? ComedianOnboardingModel())
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                header

                LaughTrackSearchField(placeholder: "Search comedians", text: $model.searchText) {
                    Button {
                        Task {
                            await model.search(model.searchText, apiClient: apiClient, favorites: favorites)
                        }
                    } label: {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Search comedians")
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingSearchButton)
                }
                .modifier(SearchFieldInputBehavior())
                .onSubmit {
                    Task {
                        await model.search(model.searchText, apiClient: apiClient, favorites: favorites)
                    }
                }
                .accessibilityIdentifier(LaughTrackViewTestID.onboardingSearchField)

                comedianSection

                notificationSection

                actionSection
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, theme.spacing.xxl)
        }
        .background(tokens.colors.canvas.ignoresSafeArea())
        .task {
            guard model.comedians.isEmpty else { return }
            await model.loadInitialComedians(apiClient: apiClient, favorites: favorites)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingScreen)
    }

    private var header: some View {
        let tokens = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text("Pick comedians to follow")
                .font(tokens.typography.hero)
                .foregroundStyle(tokens.colors.textPrimary)

            Text("Choose favorites now, or skip and start browsing. Aim for 3 so LaughTrack can surface better show alerts.")
                .font(tokens.typography.body)
                .foregroundStyle(tokens.colors.textSecondary)

            Text("\(model.favoriteCount)/\(model.suggestedFavoriteTarget) selected")
                .font(tokens.typography.metadata)
                .foregroundStyle(tokens.colors.accentStrong)
                .accessibilityIdentifier(LaughTrackViewTestID.onboardingFavoriteCount)
        }
    }

    @ViewBuilder
    private var comedianSection: some View {
        switch model.phase {
        case .idle, .loading:
            ProgressView("Loading comedians")
                .frame(maxWidth: .infinity, alignment: .center)
        case .failure(let message):
            InlineStatusMessage(message: message)
        case .loaded, .saving:
            LazyVStack(spacing: theme.spacing.md) {
                ForEach(model.comedians, id: \.uuid) { comedian in
                    ComedianOnboardingRow(
                        comedian: comedian,
                        isFavorite: favorites.value(for: comedian.uuid, fallback: comedian.isFavorite),
                        isPending: favorites.isPending(comedian.uuid)
                    ) {
                        await model.toggleFavorite(
                            uuid: comedian.uuid,
                            apiClient: apiClient,
                            favorites: favorites,
                            authManager: authManager
                        )
                    }
                }
            }
        }
    }

    private var notificationSection: some View {
        LaughTrackCard(tone: .standard, density: .compact) {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                Text("Show alerts")
                    .font(theme.laughTrackTokens.typography.cardTitle)
                    .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)

                Toggle("Email alerts", isOn: $model.emailAlertsEnabled)
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingEmailToggle)

                Toggle("Push alerts", isOn: $model.pushAlertsEnabled)
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingPushToggle)
            }
        }
    }

    private var actionSection: some View {
        VStack(spacing: theme.spacing.sm) {
            LaughTrackButton(model.phase == .saving ? "Saving..." : "Continue", systemImage: "checkmark") {
                Task {
                    await saveNotificationPreferences()
                    await model.complete(apiClient: apiClient, authManager: authManager)
                }
            }
            .disabled(!model.canContinue)
            .accessibilityIdentifier(LaughTrackViewTestID.onboardingContinueButton)

            LaughTrackButton("Skip", systemImage: "arrow.right", tone: .secondary) {
                Task {
                    await model.skip(apiClient: apiClient, authManager: authManager)
                }
            }
            .disabled(!model.canContinue)
            .accessibilityIdentifier(LaughTrackViewTestID.onboardingSkipButton)
        }
    }

    private func saveNotificationPreferences() async {
        await model.setNotificationPreferences(
            emailEnabled: model.emailAlertsEnabled,
            pushEnabled: model.pushAlertsEnabled,
            store: notificationPreferenceStore,
            syncClient: notificationPreferenceSyncClient
        )
    }
}

private struct ComedianOnboardingRow: View {
    @Environment(\.appTheme) private var theme

    let comedian: Components.Schemas.ComedianSearchItem
    let isFavorite: Bool
    let isPending: Bool
    let toggleFavorite: () async -> Void

    var body: some View {
        LaughTrackCard(tone: isFavorite ? .accent : .standard, density: .compact) {
            HStack(spacing: theme.spacing.md) {
                RemoteImageView(
                    urlString: comedian.imageUrl,
                    aspectRatio: 1
                )
                .frame(width: 60, height: 60)

                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text(comedian.name)
                        .font(theme.laughTrackTokens.typography.cardTitle)
                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)

                    Text(comedian.showCount == 1 ? "1 tracked show" : "\(comedian.showCount) tracked shows")
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                }

                Spacer(minLength: 0)

                FavoriteButton(isFavorite: isFavorite, isPending: isPending, action: toggleFavorite)
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingComedianFavoriteButton(comedian.id))
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingComedianRow(comedian.id))
    }
}
