import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum HomeContentSection: String, Hashable {
    case showsTonight = "shows_tonight"
    case followedComedianShows = "followed_comedian_shows"
    case thisWeek = "trending_this_week"
    case comedians = "trending_comedians"
    case clubs = "popular_clubs"
    case podcasts = "trending_podcasts"

    static func sections(for primitive: SearchRootModel.Pivot?) -> [HomeContentSection] {
        switch primitive {
        case .shows:
            return [.showsTonight, .followedComedianShows, .thisWeek]
        case .comedians:
            return [.comedians]
        case .clubs:
            return [.clubs]
        case .podcasts:
            return [.podcasts]
        default:
            return [.showsTonight, .followedComedianShows, .thisWeek, .comedians, .clubs, .podcasts]
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

    @ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @StateObject private var railPlanModel = HomeDiscoverRailPlanModel()

    init(
        apiClient: Client,
        signedOutMessage: String?,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
        self.nearbyPreferenceStore = nearbyPreferenceStore
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        // Native ScrollView keeps the exact offset as this stable tab is covered
        // and revealed. Re-scrolling to a section onAppear loses the position
        // within that section, including during an interactive back cancellation.
        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                HomeDiscoverHeader(
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                    nearbyPreferenceStore: nearbyPreferenceStore,
                    profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self),
                    currentUser: authManager.currentUser
                )

                contentSections

                if selectedPrimitive == nil,
                   let failure = railPlanModel.failure(for: railPlanRequestKey) {
                    VStack(alignment: .leading, spacing: theme.spacing.sm) {
                        Text(failure.message)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                        LaughTrackButton("Retry", systemImage: "arrow.clockwise", tone: .secondary, density: .compact, fullWidth: false) {
                            Task { await refreshPlan(force: true) }
                        }
                        .disabled(railPlanModel.isRefreshing)
                        .accessibilityIdentifier("laughtrack.home.plan-retry")
                    }
                }
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, laughTrack.browseDensity.heroPadding)
        }
        .task(id: railPlanRequestKey) {
            guard selectedPrimitive == nil else { return }
            await refreshPlan()
        }
        .refreshable {
            guard selectedPrimitive == nil else { return }
            await refreshPlan(force: true)
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

    private func refreshPlan(force: Bool = false) async {
        await railPlanModel.refresh(
            apiClient: apiClient,
            zipCode: nearbyPreference?.zipCode,
            distanceMiles: nearbyPreference?.distanceMiles,
            sessionDiscriminator: sessionDiscriminator,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self),
            forceRefresh: force
        )
    }

    private var contentSections: some View {
        let presentation = railPlanModel.presentation(for: railPlanRequestKey)
        return Group {
            if selectedPrimitive != nil {
                legacySections
            } else {
                switch presentation {
                case .pending:
                    VStack(spacing: theme.spacing.md) {
                        ProgressView()
                        Text("Finding your next laugh…")
                            .font(theme.laughTrackTokens.typography.metadata)
                            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    }
                    .frame(maxWidth: .infinity, minHeight: 240)
                    .accessibilityElement(children: .combine)
                    .accessibilityIdentifier("laughtrack.home.plan-loading")
                    .transition(.opacity)
                case .planned(let sections):
                    if sections.isEmpty {
                        EmptyCard(
                            title: "No discoveries nearby yet",
                            message: "Try a different location or explore Search for more comedy."
                        )
                    } else {
                        ForEach(sections) { section in
                            anchoredSection(id: section.id) {
                                HomeDiscoverPlannedRail(
                                    section: section,
                                    searchNavigationBridge: searchNavigationBridge,
                                    nearbyPreference: nearbyPreference
                                )
                            }
                            .task(id: railPlanModel.measurementGeneration) {
                                if let parameters = railPlanModel.contentDidAppear(for: railPlanRequestKey) {
                                    DiscoverPerformanceMetrics.record(parameters)
                                }
                            }
                        }
                    }
                case .legacy:
                    legacySections
                }
            }
        }
        .animation(reduceMotion || presentation == .pending ? nil : .easeInOut(duration: 0.25), value: presentation.transitionKey)
    }

    private var legacySections: some View {
        ForEach(HomeContentSection.sections(for: selectedPrimitive), id: \.self) { section in
            anchoredSection(id: section.rawValue) {
                sectionContent(section)
            }
        }
    }

    private func anchoredSection<Content: View>(
        id: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        content()
            .id(id)
    }

    @ViewBuilder
    private func sectionContent(_ section: HomeContentSection) -> some View {
            switch section {
            case .showsTonight:
                showsSection(.showsTonight)
            case .followedComedianShows:
                followedComedianShowsSection
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

    private var followedComedianShowsSection: some View {
        HomeFollowedComedianShowsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: nearbyPreferenceStore,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private func showsSection(_ railKind: HomeShowRailKind) -> some View {
        HomeShowsTonightRail(
            railKind: railKind,
            apiClient: apiClient,
            nearbyPreferenceStore: nearbyPreferenceStore,
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var comediansSection: some View {
        HomeTrendingComediansRail(
            apiClient: apiClient,
            nearbyPreferenceStore: nearbyPreferenceStore,
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var clubsSection: some View {
        HomePopularClubsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: nearbyPreferenceStore,
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var podcastsSection: some View {
        HomeTrendingPodcastsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: nearbyPreferenceStore,
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var nearbyPreference: NearbyPreference? {
        nearbyPreferenceStore.preference ?? nearbyPreferenceStore.defaultPreference
    }

    private var sessionDiscriminator: String? {
        guard let userID = authManager.currentUser?.userId,
              let session = authManager.currentSession else { return nil }
        return "\(userID)|\(session.signedInAt.timeIntervalSinceReferenceDate)"
    }

    private var railPlanRequestKey: String {
        railPlanModel.requestKey(
            zipCode: nearbyPreference?.zipCode,
            distanceMiles: nearbyPreference?.distanceMiles,
            sessionDiscriminator: sessionDiscriminator
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
