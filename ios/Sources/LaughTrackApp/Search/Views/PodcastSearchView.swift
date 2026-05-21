import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastSearchView: View {
    let apiClient: Client
    @ObservedObject var model: PodcastSearchModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var isActive = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @State private var openDropdownID: String?
    @State private var feedbackMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search podcast titles",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                }

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "podcasts-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    PillSheetTrigger(
                        title: "Include all",
                        systemImage: "eye",
                        isActive: model.includeEmpty,
                        accessibilityLabel: "Include podcasts with no linked comedians",
                        accessibilityHint: model.includeEmpty
                            ? "Currently showing podcasts without linked comedians."
                            : "Currently hiding podcasts without linked comedians."
                    ) {
                        model.includeEmpty.toggle()
                    }
                }

                switch model.phase {
                case .idle, .loading:
                    PodcastsListSkeleton()
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload() },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No podcasts yet",
                            message: model.searchText.isEmpty
                                ? "No podcasts are available right now."
                                : "No podcasts matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(result.items) { podcast in
                                PodcastSearchRow(
                                    podcast: podcast,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage
                                )
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more podcasts",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore()
                                }
                            }
                        }
                    }
                }
            }
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload()
        }
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "podcasts-sort",
                    options: PodcastSortOption.allCases,
                    selected: $model.sort,
                    triggerLabel: { $0.title },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )
            }
        }
    }
}

struct PodcastSearchRow: View {
    let podcast: PodcastSearchResult
    let apiClient: Client
    @Binding var feedbackMessage: String?

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme

    var body: some View {
        let numericID = Self.numericID(for: podcast)
        let isFavorite = numericID.map { podcastFavorites.value(for: $0) } ?? false

        HStack(spacing: theme.spacing.md) {
            Button {
                if let target = podcast.navigationTarget {
                    coordinator.open(target)
                }
            } label: {
                LaughTrackEntityRow(
                    title: podcast.title,
                    subtitle: podcast.subtitle?.nonEmpty,
                    systemImage: "headphones",
                    imageURL: podcast.imageUrl,
                    design: .savedEntity
                )
            }
            .buttonStyle(.plain)
            .disabled(podcast.navigationTarget == nil)

            if let numericID {
                FavoriteButton(
                    isFavorite: isFavorite,
                    isPending: podcastFavorites.isPending(numericID)
                ) {
                    await toggle(podcastID: numericID, currentValue: isFavorite)
                }
            }
        }
    }

    private func toggle(podcastID: Int, currentValue: Bool) async {
        let result = await podcastFavorites.toggle(
            podcastID: podcastID,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )
        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: podcast.title, isFavorite: next)
        case .signInRequired:
            loginModalPresenter.present()
        case .failure(let message):
            feedbackMessage = message
        }
    }

    static func numericID(for podcast: PodcastSearchResult) -> Int? {
        guard podcast.id.hasPrefix("podcast-"),
              let value = Int(podcast.id.dropFirst("podcast-".count))
        else { return nil }
        return value
    }
}
