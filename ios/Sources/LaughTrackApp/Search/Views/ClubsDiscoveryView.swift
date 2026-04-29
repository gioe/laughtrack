import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ClubsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ClubsDiscoveryModel
    var displaysSearchInput = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Clubs",
                    title: "Clubs in reach",
                    subtitle: "Keep venues dense, tappable, and easy to scan."
                )

                if displaysSearchInput {
                    SearchField(
                        title: "Club name",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.searchText
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading clubs")
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, cache: pageCache) },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No clubs yet",
                            message: model.searchText.isEmpty
                                ? "No clubs are available right now."
                                : "No clubs matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(Array(result.items.enumerated()), id: \.offset) { _, club in
                                Button {
                                    if let id = club.id {
                                        coordinator.open(.club(id))
                                    }
                                } label: {
                                    ClubRow(club: club)
                                }
                                .buttonStyle(.plain)
                                .disabled(club.id == nil)
                                .accessibilityIdentifier(club.id.map(LaughTrackViewTestID.clubsSearchResultButton) ?? "laughtrack.clubs-search.result-missing-id")
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more clubs",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient, cache: pageCache)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.searchText) {
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubsSearchScreen)
    }
}

struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem

    var body: some View {
        LaughTrackResultRow(
            title: club.name ?? "Unknown club",
            subtitle: [club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable",
            metadata: [
                club.activeComedianCount.map { "\($0) active comedians" },
                club.showCount.map { "\($0) shows" },
            ].compactMap { $0 },
            systemImage: "building.2.fill",
            imageURL: club.imageUrl
        )
    }
}
