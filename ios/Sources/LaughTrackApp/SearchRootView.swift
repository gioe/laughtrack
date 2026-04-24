import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore
    let coordinator: NavigationCoordinator<AppRoute>
    let searchNavigationBridge: SearchNavigationBridge

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
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        self.coordinator = coordinator
        self.searchNavigationBridge = searchNavigationBridge
        _showsModel = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                LaughTrackHeroModule(
                    eyebrow: "Search",
                    title: "Search nearby comedy",
                    subtitle: model.activePivot.queryHelpText
                )

                LaughTrackCard(density: .compact) {
                    VStack(alignment: .leading, spacing: tokens.browseDensity.rowGap) {
                        LaughTrackSearchField(
                            placeholder: model.activePivot.queryPrompt,
                            text: $model.query
                        )

                        LaughTrackContextRow(
                            leading: model.contextSummary,
                            trailing: model.selectedShortcut ?? "Custom"
                        )

                        shortcutRow
                        pivotRow
                    }
                }

                activeSearchScreenWithDependencies
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.searchTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
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
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                ForEach(["Near Me", "Tonight", "This Week"], id: \.self) { shortcut in
                    Button {
                        model.selectShortcut(shortcut)
                        applyRootQueryToActivePivot()
                    } label: {
                        LaughTrackBrowseChip(
                            shortcut,
                            systemImage: shortcutSystemImage(for: shortcut),
                            tone: shortcutTone(for: shortcut)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var pivotRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                ForEach(SearchRootModel.Pivot.allCases) { pivot in
                    Button {
                        model.activePivot = pivot
                    } label: {
                        LaughTrackBrowseChip(
                            pivot.title,
                            systemImage: pivotSystemImage(for: pivot),
                            tone: model.activePivot == pivot ? .selected : .neutral
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func shortcutTone(for shortcut: String) -> LaughTrackBrowseChipTone {
        model.selectedShortcut == shortcut ? .selected : .neutral
    }

    private func shortcutSystemImage(for shortcut: String) -> String {
        switch shortcut {
        case "Tonight":
            return "moon.stars"
        case "This Week":
            return "calendar"
        default:
            return "location"
        }
    }

    private func pivotSystemImage(for pivot: SearchRootModel.Pivot) -> String {
        switch pivot {
        case .shows:
            return "music.mic"
        case .comedians:
            return "person.2"
        case .clubs:
            return "building.2"
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
        model.applyShortcutFilters(to: showsModel)
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
    }
}
