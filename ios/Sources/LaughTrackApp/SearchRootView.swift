import SwiftUI
import LaughTrackAPIClient
import LaughTrackCore

struct SearchRootView: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme
    @StateObject private var model = SearchRootModel()

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.xl) {
            TextField("Search comedy near you", text: $model.query)
                .textFieldStyle(.roundedBorder)

            HStack(spacing: theme.spacing.sm) {
                ForEach(["Near Me", "Tonight", "This Week"], id: \.self) { label in
                    Button(label) {
                        model.selectedShortcut = label
                    }
                }
            }

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
        .accessibilityIdentifier(LaughTrackViewTestID.searchTabScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Search")
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
    }

    @ViewBuilder
    private var activeSearchScreen: some View {
        switch model.activePivot {
        case .shows:
            ShowsSearchScreen(
                apiClient: apiClient,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        case .comedians:
            ComediansSearchScreen(apiClient: apiClient)
        case .clubs:
            ClubsSearchScreen(apiClient: apiClient)
        }
    }
}
