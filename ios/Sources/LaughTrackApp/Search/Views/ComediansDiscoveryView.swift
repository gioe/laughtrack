import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComediansDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ComediansDiscoveryModel
    var displaysSearchInput = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @State private var feedbackMessage: String?

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Comedians",
                    title: "Comedians in rotation",
                    subtitle: "Scan favorites and upcoming sets without leaving Search."
                )

                if displaysSearchInput {
                    SearchField(
                        title: "Comedian name",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.searchText
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading comedians")
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No comedians yet",
                            message: model.searchText.isEmpty
                                ? "No comedians are available right now."
                                : "No comedians matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(result.items, id: \.uuid) { comedian in
                                ComedianRow(
                                    comedian: comedian,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage,
                                    openDetail: { coordinator.open(.comedian(comedian.id)) }
                                )
                                .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchResultButton(comedian.id))
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more comedians",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient, favorites: favorites)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.searchText) {
            await model.reload(apiClient: apiClient, favorites: favorites)
        }
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
        .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchScreen)
    }
}

struct ComedianRow: View {
    let comedian: Components.Schemas.ComedianSearchItem
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme

    var body: some View {
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: theme.spacing.sm) {
            Button(action: openDetail) {
                LaughTrackResultRow(
                    title: comedian.name,
                    subtitle: SocialLink.links(from: comedian.socialData).first?.label,
                    metadata: ["\(comedian.showCount) upcoming"],
                    systemImage: "music.mic",
                    imageURL: comedian.imageUrl,
                    showsDisclosureIndicator: false
                )
            }
            .buttonStyle(.plain)

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired:
                    loginModalPresenter.present()
                case .failure(let message):
                    feedbackMessage = message
                }
            }
        }
    }
}
