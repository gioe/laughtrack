import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum HomeContentSection: Equatable {
    case showsTonight
    case thisWeek
    case comedians
    case clubs
    case podcasts

    static func sections(for primitive: SearchRootModel.Pivot?) -> [HomeContentSection] {
        switch primitive {
        case .shows:
            return [.showsTonight, .thisWeek]
        case .comedians:
            return [.comedians]
        case .clubs:
            return [.clubs]
        case .podcasts:
            return [.podcasts]
        default:
            return [.showsTonight, .thisWeek, .comedians, .clubs, .podcasts]
        }
    }
}

enum HomeShowRailKind: Equatable {
    case showsTonight
    case thisWeek

    var eyebrow: String? {
        switch self {
        case .showsTonight:
            // The Tonight hero cards already lead with a big "TONIGHT!"
            // marquee banner, so the shelf eyebrow would just duplicate it.
            return nil
        case .thisWeek:
            return "Coming Up"
        }
    }

    var title: String? {
        switch self {
        case .showsTonight:
            return nil
        case .thisWeek:
            return "Best shows this week"
        }
    }

    var subtitle: String? {
        switch self {
        case .showsTonight:
            return nil
        case .thisWeek:
            return nil
        }
    }

    var emptyMessage: String {
        switch self {
        case .showsTonight:
            return "No shows are listed for tonight yet."
        case .thisWeek:
            return "No upcoming shows are listed near you this week."
        }
    }

    var searchShortcut: String? {
        switch self {
        case .showsTonight:
            return "Tonight"
        case .thisWeek:
            return "This Week"
        }
    }

    var railAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightRail
        case .thisWeek:
            return "laughtrack.home.this-week-rail"
        }
    }

    var seeMoreAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightSeeMoreButton
        case .thisWeek:
            return "laughtrack.home.this-week-see-more-button"
        }
    }
}

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let selectedPrimitive: SearchRootModel.Pivot?
    let searchNavigationBridge: SearchNavigationBridge
    let onInitialHomeLoadComplete: (() -> Void)?

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        signedOutMessage: String?,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge,
        onInitialHomeLoadComplete: (() -> Void)? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
        self.onInitialHomeLoadComplete = onInitialHomeLoadComplete
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                HomeDiscoverHeader(
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self),
                    currentUser: authManager.currentUser
                )

                contentSections
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, laughTrack.browseDensity.heroPadding)
        }
        .rootScrollBottomClearance(
            theme: theme,
            isPodcastMiniPlayerVisible: podcastPlayer.currentItem != nil
        )
        .accessibilityIdentifier(LaughTrackViewTestID.homeScreen)
        .background(Color.clear)
        .navigationTitle("LaughTrack")
        .toolbar {
            ToolbarItem(placement: toolbarPlacement) {
                Button {
                    coordinator.push(AppRoute.nearMeToolbarTarget(isSignedIn: authManager.currentSession != nil))
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "person.crop.circle")
                }
                .accessibilityLabel(authManager.currentSession == nil ? "Sign in" : "Profile")
                .accessibilityIdentifier(LaughTrackViewTestID.homeSettingsButton)
            }
        }
        .modifier(LaughTrackNavigationChrome(background: .clear))
    }

    private var toolbarPlacement: ToolbarItemPlacement {
        #if os(iOS)
        .topBarTrailing
        #else
        .primaryAction
        #endif
    }

    @ViewBuilder
    private var contentSections: some View {
        ForEach(HomeContentSection.sections(for: selectedPrimitive), id: \.self) { section in
            switch section {
            case .showsTonight:
                showsSection(.showsTonight)
            case .thisWeek:
                showsSection(.thisWeek)
            case .comedians:
                comediansSection
            case .clubs:
                clubsSection
            case .podcasts:
                podcastsSection
            }
        }
    }

    private func showsSection(_ railKind: HomeShowRailKind) -> some View {
        HomeShowsTonightRail(
            railKind: railKind,
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self),
            onInitialHomeLoadComplete: onInitialHomeLoadComplete
        )
    }

    private var comediansSection: some View {
        HomeTrendingComediansRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var clubsSection: some View {
        HomePopularClubsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var podcastsSection: some View {
        HomeTrendingPodcastsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }
}

private struct HomeDiscoverHeader: View {
    @ObservedObject private var nearbyLocationController: NearbyLocationController
    @ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore
    @StateObject private var locationModel: SettingsNearbyPreferenceModel
    @State private var isLocationEditorPresented = false
    private let currentUser: AuthenticatedUser?

    @Environment(\.appTheme) private var theme

    init(
        nearbyLocationController: NearbyLocationController,
        nearbyPreferenceStore: NearbyPreferenceStore,
        profileLocationPreferenceSyncClient: (any ProfileLocationPreferenceSyncing)?,
        currentUser: AuthenticatedUser?
    ) {
        self.nearbyLocationController = nearbyLocationController
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.currentUser = currentUser
        _locationModel = StateObject(
            wrappedValue: SettingsNearbyPreferenceModel(
                nearbyLocationController: nearbyLocationController,
                syncClient: profileLocationPreferenceSyncClient
            )
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            Button {
                isLocationEditorPresented = true
            } label: {
                HomeLocationPrompt(
                    displayPreference: nearbyLocationController.preference ?? nearbyPreferenceStore.defaultPreference,
                    isExplicitPreference: nearbyLocationController.preference != nil
                )
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier(LaughTrackViewTestID.homeLocationPrompt)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .sheet(isPresented: $isLocationEditorPresented) {
            HomeLocationEditorSheet(
                model: locationModel,
                isPresented: $isLocationEditorPresented
            )
            .environment(\.appTheme, theme)
        }
        .onAppear {
            refreshProfileLocation(from: currentUser)
        }
        .onChange(of: currentUser) { user in
            refreshProfileLocation(from: user)
        }
    }

    private func refreshProfileLocation(from user: AuthenticatedUser?) {
        guard let user else { return }
        locationModel.replaceServerBackedPreference(from: user)
    }
}
