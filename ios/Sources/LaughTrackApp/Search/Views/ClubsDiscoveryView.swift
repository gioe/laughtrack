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
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var isZipEditorPresented = false
    @State private var isFilterEditorPresented = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if displaysSearchInput {
                    if let unifiedSearchText {
                        SearchField(
                            title: "Search",
                            prompt: unifiedSearchPrompt ?? "Search club names",
                            text: unifiedSearchText,
                            showsTitle: false
                        )
                    } else {
                        SearchField(
                            title: "Club name",
                            prompt: "Comedy Cellar, The Stand…",
                            text: $model.searchText
                        )
                    }
                }

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "clubs-distance",
                        selected: model.distance,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Distance \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    PillDropdownTrigger(
                        id: "clubs-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    PillSheetTrigger(
                        title: locationChipTitle,
                        systemImage: locationChipSystemImage,
                        isActive: model.activeNearbyPreference != nil,
                        accessibilityLabel: "Edit ZIP",
                        accessibilityHint: locationChipAccessibilityHint
                    ) {
                        isZipEditorPresented = true
                    }

                    PillSheetTrigger(
                        title: model.selectedFilterSlugs.count > 0 ? filterCountTitle : "Filters",
                        systemImage: "line.3.horizontal.decrease",
                        isActive: model.selectedFilterSlugs.count > 0,
                        accessibilityLabel: "Filter results"
                    ) {
                        isFilterEditorPresented = true
                    }
                }

                if let nearbyStatusMessage = model.nearbyStatusMessage {
                    InlineStatusMessage(message: nearbyStatusMessage)
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
                            message: emptyStateMessage
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            AdaptiveSearchResults(spacing: theme.spacing.md) {
                                ForEach(Array(result.items.enumerated()), id: \.offset) { _, club in
                                    ClubRow(club: club) {
                                        if let id = club.id {
                                            coordinator.open(.club(id))
                                        }
                                    }
                                    .disabled(club.id == nil)
                                }
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
        .sheet(isPresented: $isZipEditorPresented) {
            LocationFilterSheet(
                model: model,
                isPresented: $isZipEditorPresented,
                subtitle: "Set the location used for nearby clubs."
            )
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
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "clubs-distance",
                    options: ShowDistanceOption.allCases,
                    selected: $model.distance,
                    triggerLabel: { $0.title },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )

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

    private var locationChipTitle: String {
        if let activeLocationLabel = model.activeLocationLabel {
            return "Location \(activeLocationLabel)"
        }

        let draft = model.zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        return draft.isEmpty ? "Location" : "Location \(draft)"
    }

    private var locationChipSystemImage: String {
        guard let source = model.activeNearbyPreference?.source else {
            return "mappin.and.ellipse"
        }
        return source == .geolocated ? "location.fill" : "mappin.and.ellipse"
    }

    private var locationChipAccessibilityHint: String {
        guard let source = model.activeNearbyPreference?.source else {
            return "No location set."
        }
        return source == .geolocated ? "Detected from device location." : "Saved manually."
    }

    private var emptyStateMessage: String {
        if !model.searchText.isEmpty {
            return "No clubs matched \"\(model.searchText)\"."
        }
        if model.activeNearbyPreference != nil {
            return "No clubs matched this ZIP code. Broaden the radius or clear the location filter."
        }
        return "No clubs are available right now."
    }
}

struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem
    let action: () -> Void

    var body: some View {
        LaughTrackSearchEntityRow(
            title: Self.title(for: club),
            subtitle: Self.subtitle(for: club),
            imageURL: club.imageUrl,
            kind: .club,
            action: action,
            accessibilityIdentifier: club.id.map(LaughTrackViewTestID.clubsSearchResultButton)
                ?? "laughtrack.clubs-search.result-missing-id"
        )
    }

    static func title(for club: Components.Schemas.ClubSearchItem) -> String {
        club.name ?? "Unknown club"
    }

    static func subtitle(for club: Components.Schemas.ClubSearchItem) -> String {
        [club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable"
    }

    /// Retained for `ClubRowTests` (the metadata helper used to drive a
    /// "N active comedians • N shows" line in the row that has since been
    /// removed in favor of a cleaner subtitle-only treatment).
    static func metadata(for club: Components.Schemas.ClubSearchItem) -> [String] {
        [
            club.activeComedianCount.map { "\($0) active comedians" },
            club.showCount.map { "\($0) shows" },
        ].compactMap { $0 }
    }
}
