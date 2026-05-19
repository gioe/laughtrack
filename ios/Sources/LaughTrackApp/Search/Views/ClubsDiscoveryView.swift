import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ClubsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ClubsDiscoveryModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var displaysSearchInput = true
    var isActive = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var isFilterEditorPresented = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search club names",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                } else if displaysSearchInput {
                    SearchField(
                        title: "Club name",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.searchText
                    )
                }

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "clubs-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    PillSheetTrigger(
                        title: model.selectedFilterSlugs.count > 0 ? filterCountTitle : "Filters",
                        systemImage: "line.3.horizontal.decrease",
                        isActive: model.selectedFilterSlugs.count > 0,
                        accessibilityLabel: "Filter results"
                    ) {
                        isFilterEditorPresented = true
                    }

                    PillSheetTrigger(
                        title: "Include all",
                        systemImage: "eye",
                        isActive: model.includeEmpty,
                        accessibilityLabel: "Include clubs with no upcoming shows",
                        accessibilityHint: model.includeEmpty
                            ? "Currently showing clubs without upcoming shows."
                            : "Currently hiding clubs without upcoming shows."
                    ) {
                        model.includeEmpty.toggle()
                    }
                }

                switch model.phase {
                case .idle, .loading:
                    ClubsListSkeleton()
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
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, cache: pageCache)
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
        .accessibilityIdentifier(LaughTrackViewTestID.clubsSearchScreen)
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "clubs-sort",
                    options: ClubSortOption.allCases,
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

struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem

    var body: some View {
        LaughTrackEntityRow(
            title: Self.title(for: club),
            subtitle: Self.subtitle(for: club),
            metadata: Self.metadata(for: club),
            systemImage: "building.2.fill",
            imageURL: club.imageUrl
        )
    }

    static func title(for club: Components.Schemas.ClubSearchItem) -> String {
        club.name ?? "Unknown club"
    }

    static func subtitle(for club: Components.Schemas.ClubSearchItem) -> String {
        [club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable"
    }

    static func metadata(for club: Components.Schemas.ClubSearchItem) -> [String] {
        [
            club.activeComedianCount.map { "\($0) active comedians" },
            club.showCount.map { "\($0) shows" },
        ].compactMap { $0 }
    }
}
