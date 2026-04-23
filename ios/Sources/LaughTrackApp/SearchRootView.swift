import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let coordinator: NavigationCoordinator<AppRoute>
    let searchNavigationBridge: SearchNavigationBridge
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
        searchNavigationBridge: SearchNavigationBridge,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.coordinator = coordinator
        self.searchNavigationBridge = searchNavigationBridge
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

                shortcutRow

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
        .onReceive(searchNavigationBridge.$request.compactMap { $0 }) { request in
            model.applySeed(request.seed)
            applyRootQueryToActivePivot()
            searchNavigationBridge.clearRequest(request)
        }
    }

    private var shortcutRow: some View {
        HStack(spacing: theme.spacing.sm) {
            ForEach(["Near Me", "Tonight", "This Week"], id: \.self) { shortcut in
                Button {
                    model.selectShortcut(shortcut)
                    applyRootQueryToActivePivot()
                } label: {
                    Text(shortcut)
                        .font(theme.laughTrackTokens.typography.metadata)
                        .padding(.horizontal, theme.spacing.md)
                        .padding(.vertical, theme.spacing.sm)
                        .background(shortcutBackground(for: shortcut))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func shortcutBackground(for shortcut: String) -> Color {
        model.selectedShortcut == shortcut
            ? theme.laughTrackTokens.colors.accent.opacity(0.22)
            : theme.laughTrackTokens.colors.surface
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
        model.applyShortcutFilters(to: showsModel)
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
    }
}
