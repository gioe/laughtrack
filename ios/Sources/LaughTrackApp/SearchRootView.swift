import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let coordinator: NavigationCoordinator<AppRoute>
    let searchNavigationBridge: SearchNavigationBridge
    let isActive: Bool
    @Binding private var selectedPrimitive: SearchRootModel.Pivot

    @Environment(\.appTheme) private var theme
    @StateObject private var model = SearchRootModel()
    @StateObject private var showsModel: ShowsListModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()
    @StateObject private var podcastsModel = PodcastSearchModel()

    init(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        coordinator: NavigationCoordinator<AppRoute>,
        searchNavigationBridge: SearchNavigationBridge,
        nearbyLocationController: NearbyLocationController,
        isActive: Bool = true,
        selectedPrimitive: Binding<SearchRootModel.Pivot> = .constant(.shows)
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.coordinator = coordinator
        self.searchNavigationBridge = searchNavigationBridge
        self.isActive = isActive
        _selectedPrimitive = selectedPrimitive
        _showsModel = StateObject(
            wrappedValue: ShowsListModel(
                nearbyLocationController: nearbyLocationController,
                initialUseDateRange: false
            )
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                SearchHeader()

                activeSearchScreenWithDependencies
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, -4)
            .padding(.bottom, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.searchTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
        .task {
            model.activePivot = selectedPrimitive
            applyRootQueryToActivePivot()
        }
        .onChange(of: model.query) { _ in
            applyRootQueryToActivePivot()
        }
        .onChange(of: model.activePivot) { _ in
            selectedPrimitive = model.activePivot
            applyRootQueryToActivePivot()
        }
        .onChange(of: selectedPrimitive) { _ in
            model.activePivot = selectedPrimitive
            applyRootQueryToActivePivot()
        }
        .onReceive(searchNavigationBridge.$request.compactMap { $0 }) { request in
            model.applySeed(request.seed)
            selectedPrimitive = request.seed.pivot
            showsModel.applySearchSeedNearbyPreference(request.seed.nearbyPreference)
            applyRootQueryToActivePivot()
            searchNavigationBridge.clearRequest(request)
        }
    }

    private var activeSearchScreenWithDependencies: some View {
        activeSearchScreen
            .environmentObject(favorites)
            .navigationCoordinator(coordinator)
    }

    @ViewBuilder
    private var activeSearchScreen: some View {
        switch model.activePivot {
        case .shows:
            ShowsListView(
                apiClient: apiClient,
                model: showsModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                displaysSearchFields: false,
                isActive: isActive
            )
        case .comedians:
            ComediansDiscoveryView(
                apiClient: apiClient,
                model: comediansModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                displaysSearchInput: false,
                isActive: isActive
            )
        case .clubs:
            ClubsDiscoveryView(
                apiClient: apiClient,
                model: clubsModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                displaysSearchInput: false,
                isActive: isActive
            )
        case .podcasts:
            PodcastSearchView(
                model: podcastsModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                isActive: isActive
            )
        }
    }

    private func applyRootQueryToActivePivot() {
        model.applyShortcutFilters(to: showsModel)
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
    }
}

private struct SearchHeader: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text("Search")
                .font(tokens.typography.sectionTitle)
                .foregroundStyle(tokens.colors.textPrimary)
                .lineLimit(1)
                .minimumScaleFactor(0.85)

            Text("Find shows, comedians, clubs, and podcasts across LaughTrack.")
                .font(tokens.typography.body)
                .foregroundStyle(tokens.colors.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(LaughTrackViewTestID.searchHeader)
    }
}
