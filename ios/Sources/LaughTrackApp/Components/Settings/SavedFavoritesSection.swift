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
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
            comedianRail
            clubRail
            podcastRail
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

    @ViewBuilder
    private var comedianRail: some View {
        let phase = comedianFavorites.savedFavoritesPhase
        let isEmpty = comedianFavorites.savedFavoriteComedians.isEmpty

        if !isEmpty || phase.isLoading || phase.failure != nil {
            LaughTrackRailCard(
                title: LibrarySection.comedians.title,
                accessibilityIdentifier: LaughTrackViewTestID.favoritesComediansSection
            ) {
                VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
                    savedComedians
                    if phase.isLoading, isEmpty {
                        loadingState(
                            title: "Loading saved comedians",
                            message: "LaughTrack is fetching the comedians you follow."
                        )
                    }
                    if let failure = phase.failure {
                        failureState(failure, label: "comedian favorites") {
                            await comedianFavorites.loadSavedFavorites(
                                apiClient: apiClient,
                                authManager: authManager,
                                force: true
                            )
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var clubRail: some View {
        let phase = clubFavorites.savedFavoritesPhase
        let isEmpty = clubFavorites.savedFavoriteClubs.isEmpty

        if !isEmpty || phase.isLoading || phase.failure != nil {
            LaughTrackRailCard(
                title: LibrarySection.clubs.title,
                accessibilityIdentifier: LaughTrackViewTestID.favoritesClubsSection
            ) {
                VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
                    savedClubs
                    if phase.isLoading, isEmpty {
                        loadingState(
                            title: "Loading saved clubs",
                            message: "LaughTrack is fetching the clubs you saved."
                        )
                    }
                    if let failure = phase.failure {
                        failureState(failure, label: "club favorites") {
                            await clubFavorites.loadSavedFavorites(
                                apiClient: apiClient,
                                authManager: authManager,
                                force: true
                            )
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var podcastRail: some View {
        let phase = podcastFavorites.savedFavoritesPhase
        let isEmpty = podcastFavorites.savedFavoritePodcasts.isEmpty

        if !isEmpty || phase.isLoading || phase.failure != nil {
            LaughTrackRailCard(
                title: LibrarySection.podcasts.title,
                accessibilityIdentifier: LaughTrackViewTestID.favoritesPodcastsSection
            ) {
                VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
                    savedPodcasts
                    if phase.isLoading, isEmpty {
                        loadingState(
                            title: "Loading saved podcasts",
                            message: "LaughTrack is fetching the podcasts you saved."
                        )
                    }
                    if let failure = phase.failure {
                        failureState(failure, label: "podcast favorites") {
                            await podcastFavorites.loadSavedFavorites(
                                apiClient: apiClient,
                                authManager: authManager,
                                force: true
                            )
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var savedComedians: some View {
        if !comedianFavorites.savedFavoriteComedians.isEmpty {
            FavoriteSearchableSection(
                items: comedianFavorites.savedFavoriteComedians,
                id: \.uuid,
                searchPlaceholder: "Search saved comedians",
                pageSize: 5
            ) { comedian, query in
                comedian.name.localizedCaseInsensitiveContains(query)
            } row: { comedian in
                LaughTrackSearchEntityRow(
                    title: comedian.name,
                    imageURL: comedian.imageUrl,
                    kind: .comedian,
                    action: { coordinator.open(.comedian(comedian.id)) },
                    accessibilityIdentifier: "laughtrack.library.comedian-\(comedian.id)"
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
        }
    }

    @ViewBuilder
    private var savedClubs: some View {
        if !clubFavorites.savedFavoriteClubs.isEmpty {
            FavoriteSearchableSection(
                items: clubFavorites.savedFavoriteClubs,
                id: \.id,
                searchPlaceholder: "Search saved clubs",
                pageSize: 5
            ) { club, query in
                club.name.localizedCaseInsensitiveContains(query)
            } row: { club in
                LaughTrackSearchEntityRow(
                    title: club.name,
                    subtitle: "Saved club",
                    imageURL: club.imageUrl,
                    kind: .club,
                    action: { coordinator.open(.club(club.id)) },
                    accessibilityIdentifier: "laughtrack.library.club-\(club.id)"
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
        }
    }

    @ViewBuilder
    private var savedPodcasts: some View {
        if !podcastFavorites.savedFavoritePodcasts.isEmpty {
            FavoriteSearchableSection(
                items: podcastFavorites.savedFavoritePodcasts,
                id: \.id,
                searchPlaceholder: "Search saved podcasts",
                pageSize: 5
            ) { podcast, query in
                podcast.title.localizedCaseInsensitiveContains(query) ||
                    (podcast.authorName?.localizedCaseInsensitiveContains(query) ?? false)
            } row: { podcast in
                LaughTrackSearchEntityRow(
                    title: podcast.title,
                    subtitle: podcast.authorName,
                    imageURL: podcast.imageUrl,
                    kind: .podcast,
                    action: { coordinator.open(.podcast(podcast.id)) },
                    accessibilityIdentifier: "laughtrack.library.podcast-\(podcast.id)"
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
        }
    }

    private func loadingState(
        title: String,
        message: String
    ) -> some View {
        LaughTrackStateView(
            tone: .loading,
            title: title,
            message: message
        )
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
