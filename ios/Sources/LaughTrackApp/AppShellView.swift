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
        false
    }

    var visiblePrimitiveFilters: [SearchRootModel.Pivot] {
        switch selectedTab {
        case .search, .nearMe:
            return SearchRootModel.Pivot.allCases
        case .favorites:
            return SearchRootModel.Pivot.geoScopedCases
        }
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
    let onInitialHomeLoadComplete: (() -> Void)?

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @EnvironmentObject private var softPushPromptCoordinator: SoftPushPromptCoordinator
    @StateObject private var searchNavigationBridge = SearchNavigationBridge()
    @State private var didApplyInitialTab = false

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        favorites: ComedianFavoriteStore,
        initialTab: AppTab = .nearMe,
        shellState: AppShellState,
        onInitialHomeLoadComplete: (() -> Void)? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.favorites = favorites
        self.initialTab = initialTab
        self.shellState = shellState
        self.onInitialHomeLoadComplete = onInitialHomeLoadComplete
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
        .background(shellBackground.ignoresSafeArea())
    }

    @ViewBuilder
    private var shellBackground: some View {
        LaughTrackAtmosphereBackground()
    }

    private var showFavoritesTab: Bool {
        guard authManager.currentSession != nil else { return false }
        return !favorites.savedFavoriteComedians.isEmpty
    }

    private var tabContent: some View {
        TabView(selection: selectedTabBinding) {
            ZStack {
                LaughTrackAtmosphereBackground()
                    .ignoresSafeArea()

                HomeView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    selectedPrimitive: shellState.selectedPrimitive,
                    searchNavigationBridge: searchNavigationBridge,
                    onInitialHomeLoadComplete: onInitialHomeLoadComplete
                )
            }
            .tabItem { Label("Discover", systemImage: "sparkles") }
            .tag(AppTab.nearMe)

            ZStack {
                LaughTrackAtmosphereBackground()
                    .ignoresSafeArea()

                SearchRootView(
                    apiClient: apiClient,
                    favorites: favorites,
                    coordinator: coordinator,
                    searchNavigationBridge: searchNavigationBridge,
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    isActive: shellState.selectedTab == .search,
                    selectedPrimitive: searchPrimitiveBinding
                )
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }
            .tag(AppTab.search)

            if showFavoritesTab {
                LibraryView(
                    apiClient: apiClient,
                    selectedPrimitive: shellState.selectedPrimitive,
                    searchNavigationBridge: searchNavigationBridge
                )
                    .tabItem { Label("Favorites", systemImage: "heart.fill") }
                    .tag(AppTab.favorites)
            }
        }
        .onChange(of: showFavoritesTab) { isVisible in
            if !isVisible, shellState.selectedTab == .favorites {
                shellState.selectTab(.nearMe)
            }
        }
        .environmentObject(favorites)
        .tint(podcastPlayer.accentColorOverride ?? theme.colors.primary)
        .animation(.easeInOut(duration: 0.55), value: podcastPlayer.accentColorOverride)
        .background(shellBackground.ignoresSafeArea())
        .onReceive(searchNavigationBridge.$request.compactMap { $0 }) { _ in
            shellState.selectTab(.search)
        }
        .task {
            guard !didApplyInitialTab else { return }
            didApplyInitialTab = true
            shellState.selectTab(initialTab)
        }
#if DEBUG
        .task {
            DebugSoftPushPromptLaunch.fireIfRequested(coordinator: softPushPromptCoordinator)
        }
#endif
        .task(id: authManager.currentSession == nil) {
            if authManager.currentSession == nil {
                favorites.resetSavedFavorites()
                podcastFavorites.resetSavedFavorites()
                clubFavorites.resetSavedFavorites()
            } else {
                async let comedians: Void = favorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager
                )
                async let podcasts: Void = podcastFavorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager
                )
                async let clubs: Void = clubFavorites.loadSavedFavorites(
                    apiClient: apiClient,
                    authManager: authManager
                )
                _ = await (comedians, podcasts, clubs)
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
        .sheet(
            isPresented: softPushPresentationBinding(.promptingSheet),
            onDismiss: {
                softPushPromptCoordinator.handleSheetDismissed()
            }
        ) {
            SoftPushPromptSheet(coordinator: softPushPromptCoordinator)
                .environment(\.appTheme, theme)
        }
        .alert(
            "Turn on push notifications in Settings",
            isPresented: softPushPresentationBinding(.deniedAlert)
        ) {
            Button("Cancel", role: .cancel) {}
            Button("Open Settings") {
                softPushPromptCoordinator.openSystemSettings()
            }
        } message: {
            Text("LaughTrack can't enable push notifications until you allow them in Settings.")
        }
        .onReceive(favorites.didAddFavoriteComedian) { _ in
            let isPostOnboarding = authManager.currentUser?.comedianOnboardingCompleted == true
            Task { [softPushPromptCoordinator] in
                await softPushPromptCoordinator.handleComedianFavoriteAdded(
                    isPostOnboarding: isPostOnboarding
                )
            }
        }
        .onReceive(clubFavorites.didAddFavoriteClub) { _ in
            let isPostOnboarding = authManager.currentUser?.comedianOnboardingCompleted == true
            Task { [softPushPromptCoordinator] in
                await softPushPromptCoordinator.handleClubFavoriteAdded(
                    isPostOnboarding: isPostOnboarding
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

    // Project the coordinator's enum-typed presentation state into a
    // per-case Bool binding for SwiftUI sheet/alert modifiers. The
    // cross-surface guard (only flip back to .hidden when this binding's
    // own surface is the active one) lives on the coordinator as a pure
    // static helper so it can be unit-tested directly.
    private func softPushPresentationBinding(
        _ target: SoftPushPromptCoordinator.Presentation
    ) -> Binding<Bool> {
        Binding(
            get: { softPushPromptCoordinator.presentation == target },
            set: { newValue in
                guard !newValue else { return }
                softPushPromptCoordinator.presentation = SoftPushPromptCoordinator.nextPresentation(
                    after: target,
                    current: softPushPromptCoordinator.presentation
                )
            }
        )
    }

    private func shellHeader(safeAreaTop: CGFloat) -> some View {
        HStack(spacing: theme.spacing.sm) {
            accountHeaderButton

            primitiveFilterScroller
        }
        .padding(.horizontal, theme.spacing.lg)
        .padding(.top, AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: safeAreaTop, theme: theme))
        .padding(.bottom, theme.spacing.sm)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.clear)
    }

    // The profile button is a menu: "Notifications" opens the notification
    // center and "Settings" preserves the original tap destination (ProfileView).
    // An unread badge overlays the icon, driven by the /me notificationsUnreadCount
    // surfaced through currentUser; it clears once the center marks itself seen.
    private var accountHeaderButton: some View {
        let unreadCount = authManager.currentUser?.notificationsUnreadCount ?? 0

        return Menu {
            Button {
                coordinator.push(.notifications)
            } label: {
                Label("Notifications", systemImage: "bell")
            }
            .accessibilityIdentifier(LaughTrackViewTestID.accountNotificationsMenuItem)

            Button {
                coordinator.push(AppRoute.accountHeaderTarget())
            } label: {
                Label("Settings", systemImage: "gearshape")
            }
            .accessibilityIdentifier(LaughTrackViewTestID.accountSettingsMenuItem)
        } label: {
            shellHeaderIconLabel(systemImage: "person.crop.circle")
                .overlay(alignment: .topTrailing) {
                    if unreadCount > 0 {
                        accountUnreadBadge(count: unreadCount)
                    }
                }
        }
        .accessibilityLabel("Account")
        .accessibilityIdentifier(LaughTrackViewTestID.accountHeaderButton)
    }

    @ViewBuilder
    private func accountUnreadBadge(count: Int) -> some View {
        let tokens = theme.laughTrackTokens
        Text(count > 9 ? "9+" : "\(count)")
            .font(.system(size: 11, weight: .bold))
            .foregroundStyle(.white)
            .padding(.horizontal, 5)
            .frame(minWidth: 18, minHeight: 18)
            .background(Circle().fill(tokens.colors.accentStrong))
            .overlay(Circle().stroke(tokens.colors.canvas, lineWidth: 2))
            .offset(x: 4, y: -4)
            .accessibilityHidden(true)
    }

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }

    private func shellHeaderIconLabel(systemImage: String) -> some View {
        let tokens = theme.laughTrackTokens

        return Image(systemName: systemImage)
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

    private var primitiveFilterRow: some View {
        HStack(spacing: theme.spacing.xs) {
            ForEach(shellState.visiblePrimitiveFilters) { primitive in
                Button {
                    shellState.selectPrimitive(primitive)
                } label: {
                    primitiveFilterLabel(for: primitive)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(primitive.title)
                .accessibilityIdentifier(LaughTrackViewTestID.primitiveFilterButton(primitive.rawValue))
            }
        }
    }

    // Marquee-themed primitive filter pills. The same component renders in
    // both Search (mode switcher) and Home/Favorites (optional category filter)
    // contexts — clear fill, dashed bulb-ring border that echoes the poster
    // frames on the home rails. Selected state lights up the ring + glow.
    private func primitiveFilterLabel(for primitive: SearchRootModel.Pivot) -> some View {
        let tokens = theme.laughTrackTokens
        let isSelected = primitive == shellState.selectedPrimitive

        return Text(primitive.title)
            .font(.system(size: 12, weight: .heavy, design: .rounded))
            .tracking(1.4)
            .textCase(.uppercase)
            .foregroundStyle(isSelected ? tokens.colors.accentStrong : tokens.colors.textSecondary)
            .padding(.horizontal, 14)
            .frame(height: 34)
            .background {
                Capsule()
                    .fill(Color.black.opacity(0.98))
                    .shadow(color: .black.opacity(0.28), radius: 8, x: 0, y: 3)
            }
            .overlay {
                Capsule()
                    .strokeBorder(
                        isSelected ? tokens.colors.accentStrong : tokens.colors.accentMuted,
                        style: StrokeStyle(
                            lineWidth: isSelected ? 1.8 : 1.4,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 5]
                        )
                    )
                    .shadow(
                        color: tokens.colors.accentStrong.opacity(isSelected ? 0.55 : 0.25),
                        radius: isSelected ? 4 : 3
                    )
                    .shadow(
                        color: tokens.colors.accentStrong.opacity(isSelected ? 0.3 : 0),
                        radius: isSelected ? 9 : 0
                    )
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

enum RootScrollBottomSpacing {
    static let floatingTabBarClearance: CGFloat = 88
    static let podcastMiniPlayerClearance: CGFloat = 72

    static func padding(
        theme: AppThemeProtocol,
        isPodcastMiniPlayerVisible: Bool = false
    ) -> CGFloat {
        theme.laughTrackTokens.browseDensity.heroPadding +
            floatingTabBarClearance +
            (isPodcastMiniPlayerVisible ? podcastMiniPlayerClearance : 0)
    }
}

extension View {
    func rootScrollBottomClearance(
        theme: AppThemeProtocol,
        isPodcastMiniPlayerVisible: Bool = false
    ) -> some View {
        safeAreaInset(edge: .bottom, spacing: 0) {
            Color.clear
                .frame(height: RootScrollBottomSpacing.padding(
                    theme: theme,
                    isPodcastMiniPlayerVisible: isPodcastMiniPlayerVisible
                ))
                .accessibilityHidden(true)
        }
    }
}
