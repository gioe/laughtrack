import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComediansDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ComediansDiscoveryModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var displaysSearchInput = true
    var isActive = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @State private var feedbackMessage: String?
    @State private var isFilterEditorPresented = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Comedians",
                    title: "Comedians in rotation",
                    subtitle: "Scan favorites and upcoming sets without leaving Search."
                )

                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search comedian names",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                } else if displaysSearchInput {
                    SearchField(
                        title: "Comedian name",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.searchText
                    )
                }

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    HStack(spacing: theme.spacing.sm) {
                        PillDropdownTrigger(
                            id: "comedians-sort",
                            selected: model.sort,
                            triggerLabel: { $0.title },
                            accessibilityLabel: { "Sort \($0.title)" },
                            openDropdownID: $openDropdownID
                        )

                        Spacer(minLength: 0)
                    }

                    HStack(spacing: theme.spacing.sm) {
                        PillSheetTrigger(
                            title: model.selectedFilterSlugs.count > 0 ? filterCountTitle : "Filters",
                            systemImage: "line.3.horizontal.decrease",
                            isActive: model.selectedFilterSlugs.count > 0,
                            accessibilityLabel: "Filter results"
                        ) {
                            isFilterEditorPresented = true
                        }

                        Spacer(minLength: 0)
                    }
                }

                switch model.phase {
                case .idle, .loading:
                    ComediansListSkeleton()
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, favorites: favorites, cache: pageCache) },
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
                                    await model.loadMore(apiClient: apiClient, favorites: favorites, cache: pageCache)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, favorites: favorites, cache: pageCache)
        }
        .sheet(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: currentFilters,
                total: currentTotal,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented
            )
            .presentationDetents([.medium, .large])
        }
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
        .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchScreen)
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "comedians-sort",
                    options: PrimitiveSortOption.allCases,
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

    private var currentFilters: [Components.Schemas.Filter] {
        guard case .success(let result) = model.phase else { return [] }
        return result.filters
    }

    private var currentTotal: Int {
        guard case .success(let result) = model.phase else { return 0 }
        return result.total
    }

    private var filterCountTitle: String {
        let count = model.selectedFilterSlugs.count
        return "\(count) filter\(count == 1 ? "" : "s")"
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

        HStack(spacing: theme.spacing.md) {
            Button(action: openDetail) {
                LaughTrackEntityRow(
                    title: comedian.name,
                    subtitle: Self.upcomingShowsText(for: comedian.showCount),
                    systemImage: "music.mic",
                    imageURL: comedian.imageUrl
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

    static func upcomingShowsText(for showCount: Int) -> String {
        "\(showCount) upcoming show\(showCount == 1 ? "" : "s")"
    }
}
