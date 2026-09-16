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
    @State private var focusRequest: UUID?
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

        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: theme.spacing.md) {
                    SearchQueryEntry(pivot: model.activePivot, query: $model.query, showsModel: showsModel, focusRequest: focusRequest)
                        .id("search-query-entry")

                    activeSearchScreenWithDependencies
                }
                .padding(.horizontal, theme.spacing.lg)
                .padding(.top, theme.spacing.sm)
                .padding(.bottom, tokens.browseDensity.heroPadding)
            }
            .onChange(of: focusRequest) { _ in
                proxy.scrollTo("search-query-entry", anchor: .top)
            }
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
        .onDisappear { focusRequest = nil }
        .onChange(of: model.activePivot) { _ in
            focusRequest = nil
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
                displaysSearchFields: false,
                isActive: isActive,
                onEditSearch: { focusRequest = UUID() }
            )
        case .comedians:
            ComediansDiscoveryView(
                apiClient: apiClient,
                model: comediansModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                displaysSearchInput: false,
                isActive: isActive,
                onEditSearch: { focusRequest = UUID() }
            )
        case .clubs:
            ClubsDiscoveryView(
                apiClient: apiClient,
                model: clubsModel,
                unifiedSearchText: $model.query,
                unifiedSearchPrompt: model.activePivot.queryPrompt,
                displaysSearchInput: false,
                isActive: isActive,
                onEditSearch: { focusRequest = UUID() }
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

/// One stable entry point; entity categories retain independent drafts, while
/// Shows exposes its two explicit API constraints without combining their meaning.
struct SearchQueryEntry: View {
    let pivot: SearchRootModel.Pivot
    @Binding var query: String
    @ObservedObject var showsModel: ShowsListModel
    var focusRequest: UUID?
    @State private var showField: ShowField = .comedian
    @Environment(\.appTheme) private var theme

    enum ShowField: String, CaseIterable {
        case comedian, club
        var title: String { rawValue.capitalized }
    }

    private var input: Binding<String> {
        guard pivot == .shows else { return $query }
        return showField == .comedian ? $showsModel.comedianSearchText : $showsModel.clubSearchText
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            SearchField(
                title: pivot == .shows ? showField.title : pivot.title,
                prompt: pivot == .shows ? "\(showField.title) name" : pivot.queryPrompt,
                text: input,
                showsTitle: false,
                accessibilityIdentifier: LaughTrackViewTestID.searchRootField,
                showsClearButton: true,
                focusContext: "\(pivot.rawValue).\(showField.rawValue)",
                focusRequest: focusRequest
            )
            if pivot == .shows {
                ViewThatFits(in: .horizontal) {
                    HStack(spacing: theme.spacing.sm) { showFieldChoices }
                    VStack(alignment: .leading, spacing: theme.spacing.sm) { showFieldChoices }
                }
            }
        }
        .onChange(of: focusRequest) { _ in
            if pivot == .shows {
                showField = showsModel.comedianSearchText.isEmpty ? .club : .comedian
            }
        }
    }

    @ViewBuilder
    private var showFieldChoices: some View {
        ForEach(ShowField.allCases, id: \.self) { field in
            Button { showField = field } label: {
                LaughTrackBrowseChip(field.title, tone: showField == field ? .accent : .neutral)
                    .fixedSize(horizontal: true, vertical: false)
                    .frame(minHeight: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("laughtrack.search.shows.\(field.rawValue)")
            .accessibilityLabel("Search shows by \(field.rawValue)")
            .accessibilityAddTraits(showField == field ? [.isSelected] : [])
        }
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
