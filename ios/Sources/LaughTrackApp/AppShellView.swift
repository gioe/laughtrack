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

    var showsLocationHeader: Bool {
        selectedTab == .nearMe
    }

    var visiblePrimitiveFilters: [SearchRootModel.Pivot] {
        selectedTab == .search ? SearchRootModel.Pivot.allCases : SearchRootModel.Pivot.geoScopedCases
    }

    func selectTab(_ tab: AppTab) {
        switch tab {
        case .search:
            updateSelectedPrimitive(cachedSearchPrimitive)
        case .nearMe, .favorites:
            updateSelectedPrimitive(nil)
        }

        if selectedTab != tab {
            selectedTab = tab
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
    @State private var isHomeLocationEditorPresented = false

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
        GeometryReader { proxy in
            VStack(spacing: 0) {
                shellHeader(safeAreaTop: proxy.safeAreaInsets.top)

                tabContent
            }
            .ignoresSafeArea(edges: .top)
        }
        #if os(iOS)
        .toolbar(.hidden, for: .navigationBar)
        #endif
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
    }

    private var tabContent: some View {
        TabView(selection: selectedTabBinding) {
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                selectedPrimitive: shellState.selectedPrimitive,
                searchNavigationBridge: searchNavigationBridge
            )
                .tabItem { Label("Near Me", systemImage: "location.fill") }
                .tag(AppTab.nearMe)

            SearchRootView(
                apiClient: apiClient,
                favorites: favorites,
                coordinator: coordinator,
                searchNavigationBridge: searchNavigationBridge,
                nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                isActive: shellState.selectedTab == .search,
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
        .sheet(isPresented: $shellState.isLocationPermissionPitchPresented) {
            LocationPermissionPitchView(
                nearbyLocationController: nearbyLocationController,
                onResolved: {
                    shellState.dismissLocationPermissionPitch()
                },
                onManualZip: {
                    shellState.dismissLocationPermissionPitchForManualZip()
                    coordinator.push(.profile)
                },
                onClose: {
                    shellState.dismissLocationPermissionPitch()
                }
            )
            .environment(\.appTheme, theme)
        }
        .sheet(isPresented: $isHomeLocationEditorPresented) {
            HomeLocationFilterModal(
                nearbyLocationController: nearbyLocationController,
                isPresented: $isHomeLocationEditorPresented
            )
            .environment(\.appTheme, theme)
            .presentationDetents([.medium, .large])
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

    private func shellHeader(safeAreaTop: CGFloat) -> some View {
        HStack(spacing: theme.spacing.sm) {
            accountHeaderButton

            primitiveFilterScroller

            if shellState.showsLocationHeader {
                locationHeaderButton
            }
        }
        .padding(.horizontal, theme.spacing.lg)
        .padding(.top, AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: safeAreaTop, theme: theme))
        .padding(.bottom, theme.spacing.sm)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(theme.laughTrackTokens.colors.canvas.opacity(0.97))
    }

    private var accountHeaderButton: some View {
        shellHeaderIconButton(
            systemImage: "person.crop.circle",
            accessibilityLabel: "Account",
            accessibilityIdentifier: LaughTrackViewTestID.accountHeaderButton
        ) {
            coordinator.push(AppRoute.accountHeaderTarget())
        }
    }

    private var locationHeaderButton: some View {
        shellHeaderIconButton(
            systemImage: "mappin.and.ellipse",
            accessibilityLabel: "Location",
            accessibilityIdentifier: LaughTrackViewTestID.locationHeaderButton
        ) {
            isHomeLocationEditorPresented = true
        }
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }

    private func shellHeaderIconButton(
        systemImage: String,
        accessibilityLabel: String,
        accessibilityIdentifier: String,
        action: @escaping () -> Void
    ) -> some View {
        let tokens = theme.laughTrackTokens

        return Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 32, weight: .semibold))
                .foregroundStyle(tokens.colors.textPrimary)
                .frame(width: AccountHeaderLayout.buttonSize, height: AccountHeaderLayout.buttonSize)
                .background {
                    Circle()
                        .fill(tokens.colors.surfaceElevated.opacity(0.94))
                        .shadow(color: .black.opacity(0.08), radius: 12, x: 0, y: 6)
                }
                .overlay {
                    Circle()
                        .stroke(tokens.colors.borderSubtle, lineWidth: 1)
                }
        }
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier(accessibilityIdentifier)
    }

    private var primitiveFilterRow: some View {
        HStack(spacing: theme.spacing.xs) {
            ForEach(shellState.visiblePrimitiveFilters) { primitive in
                Button {
                    shellState.selectPrimitive(primitive)
                } label: {
                    Text(primitive.title)
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(primitive == shellState.selectedPrimitive ? theme.laughTrackTokens.colors.textInverse : theme.laughTrackTokens.colors.textPrimary)
                        .padding(.horizontal, 12)
                        .frame(height: 34)
                        .background {
                            Capsule()
                                .fill(primitive == shellState.selectedPrimitive ? theme.laughTrackTokens.colors.accentStrong : theme.laughTrackTokens.colors.surfaceElevated.opacity(0.94))
                                .shadow(color: .black.opacity(0.08), radius: 10, x: 0, y: 5)
                        }
                        .overlay {
                            Capsule()
                                .stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel(primitive.title)
                .accessibilityIdentifier(LaughTrackViewTestID.primitiveFilterButton(primitive.rawValue))
            }
        }
    }

    private var primitiveFilterScroller: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            primitiveFilterRow
                .padding(.horizontal, 1)
                .padding(.vertical, 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

enum AccountHeaderLayout {
    static let buttonSize: CGFloat = 48
    private static let tallSafeAreaThreshold: CGFloat = 44
    private static let tallSafeAreaOverlap: CGFloat = 18

    static func accountHeaderTopPadding(safeAreaTop: CGFloat, theme: AppThemeProtocol) -> CGFloat {
        let overlap = safeAreaTop > tallSafeAreaThreshold ? tallSafeAreaOverlap : 0
        return max(theme.spacing.xs, safeAreaTop - overlap + theme.spacing.xs)
    }
}
