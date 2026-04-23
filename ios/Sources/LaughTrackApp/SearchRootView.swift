import SwiftUI
import LaughTrackAPIClient
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme
    @StateObject private var model = SearchRootModel()
    @StateObject private var showsModel: ShowsDiscoveryModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()

    init(
        apiClient: Client,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
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
                TextField("Search comedy near you", text: $model.query)
                    .textFieldStyle(.roundedBorder)

                Picker("Entity", selection: $model.activePivot) {
                    ForEach(SearchRootModel.Pivot.allCases) { pivot in
                        Text(pivot.title).tag(pivot)
                    }
                }
                .pickerStyle(.segmented)

                activeSearchScreen
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

    @ViewBuilder
    private var activeSearchScreen: some View {
        switch model.activePivot {
        case .shows:
            ShowsDiscoveryView(
                apiClient: apiClient,
                model: showsModel,
                showsSearchFields: false
            )
        case .comedians:
            ComediansDiscoveryView(
                apiClient: apiClient,
                model: comediansModel,
                showsSearchInput: false
            )
        case .clubs:
            ClubsDiscoveryView(
                apiClient: apiClient,
                model: clubsModel,
                showsSearchInput: false
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
