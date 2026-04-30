import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class AppShellState: ObservableObject {
    @Published var selectedTab: AppTab = .nearMe
    @Published var selectedPrimitive: SearchRootModel.Pivot?
    @Published var isLocationPermissionPitchPresented = false

    private var cachedSearchPrimitive: SearchRootModel.Pivot = .shows
    private var suppressLocationPermissionPitchThisSession = false

    var resolvedSearchPrimitive: SearchRootModel.Pivot {
        selectedPrimitive ?? cachedSearchPrimitive
    }

    func selectTab(_ tab: AppTab) {
        if selectedTab != tab {
            selectedTab = tab
        }

        switch tab {
        case .search:
            updateSelectedPrimitive(cachedSearchPrimitive)
        case .nearMe, .favorites:
            updateSelectedPrimitive(nil)
        }
    }

    func selectPrimitive(_ primitive: SearchRootModel.Pivot) {
        if selectedTab == .nearMe || selectedTab == .favorites {
            updateSelectedPrimitive(selectedPrimitive == primitive ? nil : primitive)
            return
        }

        cachedSearchPrimitive = primitive
        updateSelectedPrimitive(primitive)

        if selectedTab != .search {
            selectedTab = .search
        }
    }

    func setSearchPrimitive(_ primitive: SearchRootModel.Pivot) {
        cachedSearchPrimitive = primitive
        if selectedTab == .search {
            updateSelectedPrimitive(primitive)
        }
    }

    func selectLocationHeader(hasNearbyPreference: Bool) -> LocationHeaderAction {
        if hasNearbyPreference || suppressLocationPermissionPitchThisSession {
            isLocationPermissionPitchPresented = false
            return .openSettings
        }

        isLocationPermissionPitchPresented = true
        return .presentPermissionPitch
    }

    func dismissLocationPermissionPitch() {
        isLocationPermissionPitchPresented = false
    }

    func dismissLocationPermissionPitchForManualZip() {
        suppressLocationPermissionPitchThisSession = true
        dismissLocationPermissionPitch()
    }

    private func updateSelectedPrimitive(_ primitive: SearchRootModel.Pivot?) {
        if selectedPrimitive != primitive {
            selectedPrimitive = primitive
        }
    }
}

enum LocationHeaderAction {
    case presentPermissionPitch
    case openSettings
}

@MainActor
struct AppShellView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let favorites: ComedianFavoriteStore
    let initialTab: AppTab
    @ObservedObject var shellState: AppShellState

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @StateObject private var searchNavigationBridge = SearchNavigationBridge()

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        favorites: ComedianFavoriteStore,
        initialTab: AppTab = .nearMe,
        shellState: AppShellState
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.favorites = favorites
        self.initialTab = initialTab
        self.shellState = shellState
    }

    var body: some View {
        tabContent
    }

    private var tabContent: some View {
        TabView(selection: selectedTabBinding) {
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                selectedPrimitive: shellState.selectedPrimitive
            )
                .tabItem { Label("Near Me", systemImage: "location.fill") }
                .tag(AppTab.nearMe)

            SearchRootView(
                apiClient: apiClient,
                favorites: favorites,
                coordinator: coordinator,
                searchNavigationBridge: searchNavigationBridge,
                nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                selectedPrimitive: searchPrimitiveBinding
            )
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
                .tag(AppTab.search)

            LibraryView(apiClient: apiClient, selectedPrimitive: shellState.selectedPrimitive)
                .tabItem { Label("Favorites", systemImage: "heart.fill") }
                .tag(AppTab.favorites)
        }
        .environmentObject(favorites)
        .tint(theme.colors.primary)
        .onReceive(searchNavigationBridge.$request.compactMap { $0 }) { _ in
            shellState.selectTab(.search)
        }
        .task(id: initialTab) {
            shellState.selectTab(initialTab)
        }
        .task(id: authManager.currentSession == nil) {
            if authManager.currentSession == nil {
                favorites.resetSavedFavorites()
            } else {
                await favorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager
                )
            }
        }
    }

    private var selectedTabBinding: Binding<AppTab> {
        Binding(
            get: { shellState.selectedTab },
            set: { shellState.selectTab($0) }
        )
    }

    private var searchPrimitiveBinding: Binding<SearchRootModel.Pivot> {
        Binding(
            get: { shellState.resolvedSearchPrimitive },
            set: { shellState.setSearchPrimitive($0) }
        )
    }
}

enum AccountHeaderLayout {
    static let buttonSize: CGFloat = 48

    static func accountHeaderTopPadding(safeAreaTop: CGFloat, theme: AppThemeProtocol) -> CGFloat {
        safeAreaTop + theme.spacing.xs
    }
}
