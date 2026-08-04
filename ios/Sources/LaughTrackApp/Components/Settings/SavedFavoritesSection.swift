import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SavedFavoritesSection: View {
    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var comedianFavorites: ComedianFavoriteStore
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @Environment(\.appTheme) private var theme
    @State private var feedbackMessage: String?

    var body: some View {
        Group {
            if shouldShowSection {
                LaughTrackRailCard(
                    eyebrow: "Your collection",
                    title: LibrarySection.saved.title,
                    accessibilityIdentifier: LaughTrackViewTestID.libraryFavoritesSection
                ) {
                    VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
                        savedComedians
                        savedClubs
                        savedPodcasts

                        if isLoading, !hasSavedItems {
                            LaughTrackStateView(
                                tone: .loading,
                                title: "Loading your saved favorites",
                                message: "LaughTrack is fetching the comedians, clubs, and podcasts you follow."
                            )
                        }

                        failures
                    }
                }
            }
        }
        .alert(
            "Couldn’t update Saved",
            isPresented: Binding(
                get: { feedbackMessage != nil },
                set: { if !$0 { feedbackMessage = nil } }
            )
        ) {
            Button("OK", role: .cancel) { feedbackMessage = nil }
        } message: {
            Text(feedbackMessage ?? "Please try again.")
        }
    }

    private var hasSavedItems: Bool {
        !comedianFavorites.savedFavoriteComedians.isEmpty ||
            !clubFavorites.savedFavoriteClubs.isEmpty ||
            !podcastFavorites.savedFavoritePodcasts.isEmpty
    }

    private var isLoading: Bool {
        comedianFavorites.savedFavoritesPhase.isLoading ||
            clubFavorites.savedFavoritesPhase.isLoading ||
            podcastFavorites.savedFavoritesPhase.isLoading
    }

    private var shouldShowSection: Bool {
        hasSavedItems || isLoading || hasFailure
    }

    private var hasFailure: Bool {
        comedianFavorites.savedFavoritesPhase.failure != nil ||
            clubFavorites.savedFavoritesPhase.failure != nil ||
            podcastFavorites.savedFavoritesPhase.failure != nil
    }

    @ViewBuilder
    private var savedComedians: some View {
        if !comedianFavorites.savedFavoriteComedians.isEmpty {
            savedGroupTitle("Comedians")
            FavoriteSearchableSection(
                items: comedianFavorites.savedFavoriteComedians,
                id: \.uuid,
                searchPlaceholder: "Search saved comedians"
            ) { comedian, query in
                comedian.name.localizedCaseInsensitiveContains(query)
            } row: { comedian in
                LaughTrackEntityRow(
                    title: comedian.name,
                    subtitle: Self.comedianSubtitle(for: comedian),
                    systemImage: ArtworkFallbackKind.person.systemImage,
                    imageURL: comedian.imageUrl,
                    showsDisclosureIndicator: true,
                    design: .savedEntity,
                    action: { coordinator.open(.comedian(comedian.id)) }
                ) {
                    FavoriteButton(
                        isFavorite: true,
                        isPending: comedianFavorites.isPending(comedian.uuid)
                    ) {
                        let result = await comedianFavorites.toggle(
                            uuid: comedian.uuid,
                            currentValue: true,
                            apiClient: apiClient,
                            authManager: authManager
                        )
                        handle(result)
                    }
                }
            }
            .accessibilityIdentifier(LaughTrackViewTestID.favoritesComediansSection)
        }
    }

    @ViewBuilder
    private var savedClubs: some View {
        if !clubFavorites.savedFavoriteClubs.isEmpty {
            savedGroupTitle("Clubs")
            FavoriteSearchableSection(
                items: clubFavorites.savedFavoriteClubs,
                id: \.id,
                searchPlaceholder: "Search saved clubs"
            ) { club, query in
                club.name.localizedCaseInsensitiveContains(query)
            } row: { club in
                LaughTrackEntityRow(
                    title: club.name,
                    subtitle: "Saved club",
                    systemImage: ArtworkFallbackKind.club.systemImage,
                    imageURL: club.imageUrl,
                    showsDisclosureIndicator: true,
                    design: .savedEntity,
                    action: { coordinator.open(.club(club.id)) }
                ) {
                    FavoriteButton(
                        isFavorite: true,
                        isPending: clubFavorites.isPending(club.id)
                    ) {
                        let result = await clubFavorites.toggle(
                            clubId: club.id,
                            currentValue: true,
                            apiClient: apiClient,
                            authManager: authManager
                        )
                        handle(result)
                    }
                }
            }
            .accessibilityIdentifier(LaughTrackViewTestID.favoritesClubsSection)
        }
    }

    @ViewBuilder
    private var savedPodcasts: some View {
        if !podcastFavorites.savedFavoritePodcasts.isEmpty {
            savedGroupTitle("Podcasts")
            FavoriteSearchableSection(
                items: podcastFavorites.savedFavoritePodcasts,
                id: \.id,
                searchPlaceholder: "Search saved podcasts"
            ) { podcast, query in
                podcast.title.localizedCaseInsensitiveContains(query) ||
                    (podcast.authorName?.localizedCaseInsensitiveContains(query) ?? false)
            } row: { podcast in
                LaughTrackEntityRow(
                    title: podcast.title,
                    subtitle: podcast.authorName,
                    metadata: [Self.episodeCount(for: podcast)],
                    systemImage: ArtworkFallbackKind.podcast.systemImage,
                    imageURL: podcast.imageUrl,
                    showsDisclosureIndicator: true,
                    design: .savedEntity,
                    action: { coordinator.open(.podcast(podcast.id)) }
                ) {
                    FavoriteButton(
                        isFavorite: true,
                        isPending: podcastFavorites.isPending(podcast.id)
                    ) {
                        let result = await podcastFavorites.toggle(
                            podcastID: podcast.id,
                            currentValue: true,
                            apiClient: apiClient,
                            authManager: authManager
                        )
                        handle(result)
                    }
                }
            }
            .accessibilityIdentifier(LaughTrackViewTestID.favoritesPodcastsSection)
        }
    }

    @ViewBuilder
    private var failures: some View {
        if let failure = comedianFavorites.savedFavoritesPhase.failure {
            failureState(failure, label: "comedian favorites") {
                await comedianFavorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager,
                    force: true
                )
            }
        }
        if let failure = clubFavorites.savedFavoritesPhase.failure {
            failureState(failure, label: "club favorites") {
                await clubFavorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager,
                    force: true
                )
            }
        }
        if let failure = podcastFavorites.savedFavoritesPhase.failure {
            failureState(failure, label: "podcast favorites") {
                await podcastFavorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager,
                    force: true
                )
            }
        }
    }

    private func savedGroupTitle(_ title: String) -> some View {
        Text(title)
            .font(theme.laughTrackTokens.typography.eyebrow)
            .foregroundStyle(theme.colors.textSecondary)
            .textCase(.uppercase)
    }

    private func failureState(
        _ failure: LoadFailure,
        label: String,
        retry: @escaping () async -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            LaughTrackStateView(
                tone: .error,
                title: "Couldn’t load \(label)",
                message: failure.message
            )
            LaughTrackButton("Retry \(label)", systemImage: "arrow.clockwise") {
                Task { await retry() }
            }
        }
    }

    private func handle(_ result: ComedianFavoriteStore.ToggleResult) {
        switch result {
        case .updated:
            break
        case .signInRequired(let message), .failure(let message):
            feedbackMessage = message
        }
    }

    private func handle(_ result: ClubFavoriteStore.ToggleResult) {
        switch result {
        case .updated:
            break
        case .signInRequired(let message), .failure(let message):
            feedbackMessage = message
        }
    }

    private func handle(_ result: PodcastFavoriteStore.ToggleResult) {
        switch result {
        case .updated:
            break
        case .signInRequired(let message), .failure(let message):
            feedbackMessage = message
        }
    }

    private static func comedianSubtitle(for comedian: Components.Schemas.ComedianSearchItem) -> String {
        comedian.showCount == 1
            ? "1 tracked show appearance"
            : "\(comedian.showCount) tracked show appearances"
    }

    private static func episodeCount(for podcast: Components.Schemas.FavoritePodcastItem) -> String {
        podcast.episodeCount == 1 ? "1 episode" : "\(podcast.episodeCount) episodes"
    }
}

private extension ComedianFavoriteStore.SavedFavoritesPhase {
    var isLoading: Bool {
        switch self {
        case .idle, .loading: return true
        case .loaded, .empty, .failure: return false
        }
    }

    var failure: LoadFailure? {
        guard case .failure(let failure) = self else { return nil }
        return failure
    }
}

private extension ClubFavoriteStore.SavedFavoritesPhase {
    var isLoading: Bool {
        switch self {
        case .idle, .loading: return true
        case .loaded, .empty, .failure: return false
        }
    }

    var failure: LoadFailure? {
        guard case .failure(let failure) = self else { return nil }
        return failure
    }
}

private extension PodcastFavoriteStore.SavedFavoritesPhase {
    var isLoading: Bool {
        switch self {
        case .idle, .loading: return true
        case .loaded, .empty, .failure: return false
        }
    }

    var failure: LoadFailure? {
        guard case .failure(let failure) = self else { return nil }
        return failure
    }
}
