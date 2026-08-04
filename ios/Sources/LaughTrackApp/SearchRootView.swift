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
    @StateObject private var clubsModel: ClubsDiscoveryModel
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
        _clubsModel = StateObject(
            wrappedValue: ClubsDiscoveryModel(
                nearbyLocationController: nearbyLocationController
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
                if model.activePivot != .shows {
                    SearchField(
                        title: "Search",
                        prompt: model.activePivot.queryPrompt,
                        text: $model.query,
                        showsTitle: false,
                        accessibilityIdentifier: LaughTrackViewTestID.searchRootField
                    )
                }

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
        .background(Color.clear)
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: .clear))
        .task {
            model.activePivot = selectedPrimitive
            applyDefaultNearbyPreferenceToSearchModels()
            applyRootQueryToActivePivot()
        }
        .onChange(of: nearbyPreferenceStore.preference) { _ in
            applyDefaultNearbyPreferenceToSearchModels()
        }
        .onChange(of: nearbyPreferenceStore.defaultPreference) { _ in
            applyDefaultNearbyPreferenceToSearchModels()
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
            switch request.seed.pivot {
            case .shows:
                showsModel.applySearchSeedNearbyPreference(request.seed.nearbyPreference)
                showsModel.applySearchSeed(request.seed.showSearch ?? ShowSearchSeed())
                model.applyShortcutFilters(to: showsModel)
            case .clubs:
                clubsModel.applySearchSeedNearbyPreference(request.seed.nearbyPreference)
            case .comedians, .podcasts:
                break
            }
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
                displaysSearchInput: false,
                isActive: isActive
            )
        }
    }

    private func applyRootQueryToActivePivot() {
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
    }

    private func applyDefaultNearbyPreferenceToSearchModels() {
        let preference = nearbyPreferenceStore.preference ?? nearbyPreferenceStore.defaultPreference
        showsModel.applyDefaultNearbyPreference(preference)
        clubsModel.applyDefaultNearbyPreference(preference)
    }
}

enum SearchResultsComposition: Equatable {
    case compactList
    case regularGrid

    static func resolve(horizontalSizeClass: UserInterfaceSizeClass?) -> Self {
        horizontalSizeClass == .regular ? .regularGrid : .compactList
    }
}

struct AdaptiveSearchResults<Content: View>: View {
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    private let spacing: CGFloat
    private let content: Content

    init(spacing: CGFloat, @ViewBuilder content: () -> Content) {
        self.spacing = spacing
        self.content = content()
    }

    @ViewBuilder
    var body: some View {
        switch SearchResultsComposition.resolve(horizontalSizeClass: horizontalSizeClass) {
        case .compactList:
            VStack(alignment: .leading, spacing: spacing) {
                content
            }
        case .regularGrid:
            LazyVGrid(columns: regularColumns, alignment: .leading, spacing: spacing) {
                content
            }
        }
    }

    private var regularColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: spacing, alignment: .top),
            GridItem(.flexible(), spacing: spacing, alignment: .top),
        ]
    }
}
