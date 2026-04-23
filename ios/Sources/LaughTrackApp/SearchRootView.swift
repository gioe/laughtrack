import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let coordinator: NavigationCoordinator<AppRoute>
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme
    @StateObject private var model = SearchRootModel()
    @StateObject private var showsModel: ShowsDiscoveryModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()

    init(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        coordinator: NavigationCoordinator<AppRoute>,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.coordinator = coordinator
        self.nearbyPreferenceStore = nearbyPreferenceStore
        _showsModel = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: NearbyLocationController(
                    store: nearbyPreferenceStore,
                    resolver: LaughTrackCore.CurrentLocationZipResolver()
                )
            )
        )
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                TextField(model.activePivot.queryPrompt, text: $model.query)
                    .textFieldStyle(.roundedBorder)

                Text(model.activePivot.queryHelpText)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)

                Picker("Entity", selection: $model.activePivot) {
                    ForEach(SearchRootModel.Pivot.allCases) { pivot in
                        Text(pivot.title).tag(pivot)
                    }
                }
                .pickerStyle(.segmented)

                activeSearchScreenWithDependencies
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, theme.laughTrackTokens.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.searchTabScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
        .task {
            applyRootQueryToActivePivot()
        }
        .onChange(of: model.query) { _ in
            applyRootQueryToActivePivot()
        }
        .onChange(of: model.activePivot) { _ in
            applyRootQueryToActivePivot()
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
            ShowsDiscoveryView(
                apiClient: apiClient,
                model: showsModel,
                displaysSearchFields: false
            )
        case .comedians:
            ComediansDiscoveryView(
                apiClient: apiClient,
                model: comediansModel,
                displaysSearchInput: false
            )
        case .clubs:
            ClubsDiscoveryView(
                apiClient: apiClient,
                model: clubsModel,
                displaysSearchInput: false
            )
        }
    }

    private func applyRootQueryToActivePivot() {
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
    }
}
