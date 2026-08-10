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

enum HomeScrollRetention {
    static func visibleSection(
        from offsets: [HomeContentSection: CGFloat],
        threshold: CGFloat = 24
    ) -> HomeContentSection? {
        visibleValue(from: offsets, threshold: threshold)
    }

    static func visibleSection(
        from offsets: [String: CGFloat],
        threshold: CGFloat = 24
    ) -> String? {
        visibleValue(from: offsets, threshold: threshold)
    }

    private static func visibleValue<Section: Hashable>(
        from offsets: [Section: CGFloat],
        threshold: CGFloat
    ) -> Section? {
        let passed = offsets.filter { $0.value <= threshold }
        if let nearestPassed = passed.max(by: { $0.value < $1.value }) {
            return nearestPassed.key
        }
        return offsets.min(by: { $0.value < $1.value })?.key
    }

    static func restorableSection(
        _ retainedSection: HomeContentSection?,
        among sections: [HomeContentSection]
    ) -> HomeContentSection? {
        restorableValue(retainedSection, among: sections)
    }

    static func restorableSection(
        _ retainedSection: String?,
        among sections: [String]
    ) -> String? {
        restorableValue(retainedSection, among: sections)
    }

    private static func restorableValue<Section: Equatable>(
        _ retainedSection: Section?,
        among sections: [Section]
    ) -> Section? {
        guard let retainedSection, sections.contains(retainedSection) else {
            return sections.first
        }
        return retainedSection
    }
}

private struct HomeSectionOffsetPreferenceKey: PreferenceKey {
    static var defaultValue: [String: CGFloat] = [:]

    static func reduce(
        value: inout [String: CGFloat],
        nextValue: () -> [String: CGFloat]
    ) {
        value.merge(nextValue(), uniquingKeysWith: { _, latest in latest })
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

    @ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var railPlanModel = HomeDiscoverRailPlanModel()
    @State private var retainedSectionID: String?
    @State private var hasAppeared = false
    @State private var hasReportedInitialLoad = false

    init(
        apiClient: Client,
        signedOutMessage: String?,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge,
        nearbyPreferenceStore: NearbyPreferenceStore,
        onInitialHomeLoadComplete: (() -> Void)? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.onInitialHomeLoadComplete = onInitialHomeLoadComplete
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                    HomeDiscoverHeader(
                        nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                        nearbyPreferenceStore: nearbyPreferenceStore,
                        profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self),
                        currentUser: authManager.currentUser
                    )

                    contentSections
                }
                .padding(.horizontal, theme.spacing.lg)
                .padding(.top, theme.spacing.sm)
                .padding(.bottom, laughTrack.browseDensity.heroPadding)
            }
            .coordinateSpace(name: "laughtrack.home.scroll")
            .onPreferenceChange(HomeSectionOffsetPreferenceKey.self) { offsets in
                if let visibleSection = HomeScrollRetention.visibleSection(from: offsets) {
                    retainedSectionID = visibleSection
                }
            }
            .onAppear {
                defer { hasAppeared = true }
                guard hasAppeared else { return }
                guard let sectionID = HomeScrollRetention.restorableSection(
                    retainedSectionID,
                    among: visibleSectionIDs
                ) else {
                    return
                }
                DispatchQueue.main.async {
                    proxy.scrollTo(sectionID, anchor: .top)
                }
            }
        }
        .task(id: railPlanRequestKey) {
            guard selectedPrimitive == nil else { return }
            await railPlanModel.refresh(
                apiClient: apiClient,
                zipCode: nearbyPreference?.zipCode,
                distanceMiles: nearbyPreference?.distanceMiles,
                sessionDiscriminator: sessionDiscriminator,
                cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
                persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
            )
            reportInitialLoad()
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
        if selectedPrimitive == nil, let plannedSections = railPlanModel.sections {
            ForEach(plannedSections) { section in
                anchoredSection(id: section.id) {
                    HomeDiscoverPlannedRail(
                        section: section,
                        searchNavigationBridge: searchNavigationBridge,
                        nearbyPreference: nearbyPreference
                    )
                }
            }
        } else {
            ForEach(HomeContentSection.sections(for: selectedPrimitive), id: \.self) { section in
                anchoredSection(id: section.rawValue) {
                    sectionContent(section)
                }
            }
        }
    }

    private func anchoredSection<Content: View>(
        id: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        content()
            .id(id)
            .background {
                GeometryReader { proxy in
                    Color.clear.preference(
                        key: HomeSectionOffsetPreferenceKey.self,
                        value: [
                            id: proxy.frame(in: .named("laughtrack.home.scroll")).minY,
                        ]
                    )
                }
            }
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
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self),
            onInitialHomeLoadComplete: reportInitialLoad
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

    private var visibleSectionIDs: [String] {
        if selectedPrimitive == nil, let sections = railPlanModel.sections {
            return sections.map(\.id)
        }
        return HomeContentSection.sections(for: selectedPrimitive).map(\.rawValue)
    }

    private func reportInitialLoad() {
        guard !hasReportedInitialLoad else { return }
        hasReportedInitialLoad = true
        onInitialHomeLoadComplete?()
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
