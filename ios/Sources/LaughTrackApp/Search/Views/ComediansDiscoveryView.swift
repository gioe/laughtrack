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
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @State private var feedbackMessage: String?
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

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "comedians-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    // Comedian search only: hidden entirely when the response carries no
                    // home-city options (no home-location data), mirroring web.
                    if !currentHomeCityFilters.isEmpty {
                        PillDropdownTrigger(
                            id: "comedians-home-city",
                            selected: homeCitySelection.wrappedValue,
                            triggerLabel: { $0.triggerLabel },
                            accessibilityLabel: { "Home city \($0.triggerLabel)" },
                            openDropdownID: $openDropdownID
                        )
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

                if !currentHomeCityFilters.isEmpty {
                    PillDropdownOverlay(
                        id: "comedians-home-city",
                        options: homeCityOptions,
                        selected: homeCitySelection,
                        triggerLabel: { $0.triggerLabel },
                        optionLabel: { $0.optionLabel },
                        openDropdownID: $openDropdownID,
                        anchors: anchors,
                        proxy: proxy
                    )
                }
            }
        }
    }

    private var currentFilters: [Components.Schemas.Filter] {
        guard case .success(let result) = model.phase else { return [] }
        return result.filters
    }

    private var currentHomeCityFilters: [Components.Schemas.HomeCityFilter] {
        guard case .success(let result) = model.phase else { return [] }
        return result.homeCityFilters
    }

    private var homeCityOptions: [HomeCityOption] {
        [.all] + currentHomeCityFilters.map(HomeCityOption.city)
    }

    /// Maps the model's `homeCity` token to/from the single-select option so
    /// picking a city (or "All home cities") re-queries with the new token.
    private var homeCitySelection: Binding<HomeCityOption> {
        Binding(
            get: {
                guard let token = model.homeCity,
                      let match = currentHomeCityFilters.first(where: { $0.value == token })
                else { return .all }
                return .city(match)
            },
            set: { model.homeCity = $0.token }
        )
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

/// Single-select option for the comedian home-city filter: either "all home
/// cities" (clears the filter) or a specific city from the response's
/// `homeCityFilters`. Wraps `HomeCityFilter` so the nullable "all" case can flow
/// through the non-optional `PillDropdown` single-select control.
private enum HomeCityOption: Hashable, Identifiable {
    case all
    case city(Components.Schemas.HomeCityFilter)

    var id: String { token ?? "__all_home_cities__" }

    /// The `city|state` token sent as the `homeCity` query param; nil for "all".
    var token: String? {
        if case .city(let filter) = self { return filter.value }
        return nil
    }

    /// Compact label shown on the pill trigger.
    var triggerLabel: String {
        switch self {
        case .all: return "Home city"
        case .city(let filter): return filter.label
        }
    }

    /// Full label shown in the dropdown option list (mirrors web "label (count)").
    var optionLabel: String {
        switch self {
        case .all: return "All home cities"
        case .city(let filter): return "\(filter.label) (\(filter.count))"
        }
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

    private static let headshotPhotoWidth: CGFloat = 64
    private static let headshotPhotoHeight: CGFloat = 61
    private static let headshotFrameWidth: CGFloat = 76
    private static let headshotFrameHeight: CGFloat = 73

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: theme.spacing.md) {
            Button(action: openDetail) {
                HStack(spacing: theme.spacing.md) {
                    headshot

                    VStack(alignment: .leading, spacing: 4) {
                        Text(comedian.name)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(comedian.name)

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
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.9), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var headshot: some View {
        ClubWallHeadshotFrame(
            caption: comedian.name,
            captionVisibility: .hidden,
            photoWidth: Self.headshotPhotoWidth,
            photoHeight: Self.headshotPhotoHeight,
            frameWidth: Self.headshotFrameWidth,
            frameHeight: Self.headshotFrameHeight
        ) {
            posterImage
        }
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(trimmed) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

}
