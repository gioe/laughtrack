import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let coordinator: TypedNavigationCoordinator<AppRoute>
    let searchNavigationBridge: SearchNavigationBridge
    @ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore
    let isActive: Bool
    @Binding private var selectedPrimitive: SearchRootModel.Pivot

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @StateObject private var model = SearchRootModel()
    @StateObject private var showsModel: ShowsListModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()
    @StateObject private var podcastsModel: PodcastSearchModel

    init(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        coordinator: TypedNavigationCoordinator<AppRoute>,
        searchNavigationBridge: SearchNavigationBridge,
        nearbyLocationController: NearbyLocationController,
        nearbyPreferenceStore: NearbyPreferenceStore,
        isActive: Bool = true,
        selectedPrimitive: Binding<SearchRootModel.Pivot> = .constant(.shows)
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.coordinator = coordinator
        self.searchNavigationBridge = searchNavigationBridge
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.isActive = isActive
        _selectedPrimitive = selectedPrimitive
        _showsModel = StateObject(
            wrappedValue: ShowsListModel(
                nearbyLocationController: nearbyLocationController,
                initialUseDateRange: false
            )
        )
        _podcastsModel = StateObject(
            wrappedValue: PodcastSearchModel(
                fetcher: APIPodcastSearchFetcher(apiClient: apiClient)
            )
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                SearchField(
                    title: "Search",
                    prompt: model.activePivot.queryPrompt,
                    text: $model.query,
                    showsTitle: false,
                    accessibilityIdentifier: LaughTrackViewTestID.searchRootField
                )

                activeSearchScreenWithDependencies
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, tokens.browseDensity.heroPadding)
        }
        .rootScrollBottomClearance(
            theme: theme,
            isPodcastMiniPlayerVisible: podcastPlayer.currentItem != nil
        )
        .accessibilityIdentifier(LaughTrackViewTestID.searchTabScreen)
        .background(Color.clear)
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: .clear))
        .task {
            model.activePivot = selectedPrimitive
            applyDefaultNearbyPreferenceToShows()
            applyRootQueryToActivePivot()
        }
        .onChange(of: nearbyPreferenceStore.preference) { _ in
            applyDefaultNearbyPreferenceToShows()
        }
        .onChange(of: nearbyPreferenceStore.defaultPreference) { _ in
            applyDefaultNearbyPreferenceToShows()
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
                apiClient: apiClient,
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

    private func applyDefaultNearbyPreferenceToShows() {
        showsModel.applyDefaultNearbyPreference(
            nearbyPreferenceStore.preference ?? nearbyPreferenceStore.defaultPreference
        )
    }
}
