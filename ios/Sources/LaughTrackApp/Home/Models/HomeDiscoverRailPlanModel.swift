import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeDiscoverRailSection: Identifiable, Equatable {
    enum Content: Equatable {
        case showsTonight([Components.Schemas.Show])
        case followedComedianShows([Components.Schemas.Show])
        case trendingThisWeek([Components.Schemas.Show])
        case trendingComedians([Components.Schemas.ComedianListItem])
        case popularClubs([Components.Schemas.ClubListItem])
        case podcastEpisodes([Components.Schemas.HomeFeedPodcastEpisode])
        case nearbyShows([Components.Schemas.Show])
        case dynamicShows(label: String, items: [Components.Schemas.HomeFeedDynamicRailItem])
    }

    let id: String
    let policyVersion: Int
    let rank: Int
    let content: Content
}

enum HomeDiscoverRailPlanPresentation {
    static let supportedVersion = 1
    static let itemLimit = 5
    private static let supportedDynamicRailKeys: Set<String> = [
        "just_passing_through",
        "starting_to_buzz",
        "from_your_podcasts",
    ]

    static func usesTodayStyleShowCarousel(railKey: String) -> Bool {
        supportedDynamicRailKeys.contains(railKey)
    }

    static func preferredHeadlinerID(
        railKey: String,
        item: Components.Schemas.HomeFeedDynamicRailItem
    ) -> Int? {
        guard usesTodayStyleShowCarousel(railKey: railKey) else { return nil }
        return item.performer?.id
    }

    static func preferredFavoriteHeadlinerID(
        show: Components.Schemas.Show
    ) -> Int? {
        show.lineup?.first(where: { $0.isFavorite == true })?.id
    }

    /// Returns nil when the response has no compatible iOS plan, which tells
    /// HomeView to preserve the legacy fixed sections. A compatible plan may
    /// intentionally return an empty array after unsupported and empty rails
    /// are removed.
    static func sections(
        from feed: Components.Schemas.HomeFeed
    ) -> [HomeDiscoverRailSection]? {
        guard let plan = feed.railPlan,
              plan.version == supportedVersion,
              plan.platform == .ios
        else { return nil }

        let dynamicRails = Dictionary(
            (feed.dynamicRails ?? []).map { ($0.railKey, $0) },
            uniquingKeysWith: { first, _ in first }
        )
        var seenRailKeys: Set<String> = []

        return plan.rails
            .sorted {
                if $0.position == $1.position { return $0.railKey < $1.railKey }
                return $0.position < $1.position
            }
            .compactMap { entry in
                guard seenRailKeys.insert(entry.railKey).inserted else { return nil }
                return section(
                    railKey: entry.railKey,
                    payloadKey: entry.payloadKey,
                    position: entry.position,
                    itemIDs: entry.itemIds,
                    policyVersion: plan.policyVersion,
                    feed: feed,
                    dynamicRails: dynamicRails
                )
            }
    }

    static func section(
        railKey: String,
        payloadKey: String,
        position: Int,
        itemIDs: [String],
        policyVersion: Int,
        feed: Components.Schemas.HomeFeed,
        dynamicRails: [String: Components.Schemas.HomeFeedDynamicRail]? = nil
    ) -> HomeDiscoverRailSection? {
        let content: HomeDiscoverRailSection.Content?

        switch (railKey, payloadKey) {
        case ("shows_tonight", "showsTonight"):
            if let shows = nonEmptyShows(itemIDs, from: feed.showsTonight) {
                content = .showsTonight(shows)
            } else {
                content = nil
            }
        case ("followed_comedian_shows", "followedComedianShows"):
            if let shows = nonEmptyShows(itemIDs, from: feed.followedComedianShows) {
                content = .followedComedianShows(Array(shows.prefix(itemLimit)))
            } else {
                content = nil
            }
        case ("trending_this_week", "trendingThisWeek"):
            if let shows = nonEmptyShows(itemIDs, from: feed.trendingThisWeek) {
                content = .trendingThisWeek(Array(shows.prefix(HomeShowsTonightModel.displayLimit)))
            } else {
                content = nil
            }
        case ("trending_comedians", "trendingComedians"):
            let values = select(itemIDs, from: feed.trendingComedians) { String($0.id) }
            content = values.isEmpty ? nil : .trendingComedians(values)
        case ("popular_clubs", "popularClubs"):
            let values = select(itemIDs, from: feed.popularClubs) { String($0.id) }
            content = values.isEmpty ? nil : .popularClubs(values)
        case ("trending_podcasts", "podcastEpisodes"):
            let values = select(itemIDs, from: feed.podcastEpisodes ?? []) { String($0.id) }
            content = values.isEmpty ? nil : .podcastEpisodes(Array(values.prefix(itemLimit)))
        case ("nearby_shows", "moreNearYou"):
            if let shows = nonEmptyShows(itemIDs, from: feed.moreNearYou) {
                content = .nearbyShows(shows)
            } else {
                content = nil
            }
        case (_, "dynamicRails"):
            guard supportedDynamicRailKeys.contains(railKey) else { return nil }
            let rails = dynamicRails ?? Dictionary(
                (feed.dynamicRails ?? []).map { ($0.railKey, $0) },
                uniquingKeysWith: { first, _ in first }
            )
            guard let rail = rails[railKey] else { return nil }
            var values = select(itemIDs, from: rail.items) { String($0.id) }
                .filter { !ShowAvailability.isSoldOut($0.show) }
            if usesTodayStyleShowCarousel(railKey: railKey) {
                values = Array(values.prefix(itemLimit))
            }
            content = values.isEmpty ? nil : .dynamicShows(label: rail.label, items: values)
        default:
            // Raw OpenAPI keys deliberately stay app-owned and fail-soft so a
            // future server rail does not make this client reject the feed.
            content = nil
        }

        guard let content else { return nil }
        return HomeDiscoverRailSection(
            id: railKey,
            policyVersion: policyVersion,
            rank: position,
            content: content
        )
    }

    private static func nonEmptyShows(
        _ itemIDs: [String],
        from shows: [Components.Schemas.Show]
    ) -> [Components.Schemas.Show]? {
        let values = select(itemIDs, from: shows) { String($0.id) }
            .filter { !ShowAvailability.isSoldOut($0) }
        return values.isEmpty ? nil : values
    }

    private static func select<Value>(
        _ itemIDs: [String],
        from values: [Value],
        id: (Value) -> String
    ) -> [Value] {
        let valuesByID = Dictionary(
            values.map { (id($0), $0) },
            uniquingKeysWith: { first, _ in first }
        )
        return itemIDs.compactMap { valuesByID[$0] }
    }
}

@MainActor
final class HomeDiscoverRailPlanModel: ObservableObject {
    @Published private(set) var sections: [HomeDiscoverRailSection]?

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(
        zipCode: String?,
        distanceMiles: Int?,
        sessionDiscriminator: String?
    ) -> String {
        "plan|\(sessionDiscriminator ?? "signed-out")|\(HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles))"
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        sessionDiscriminator: String?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )
        if loadedRequestKey == requestKey,
           let loadedAt,
           Date().timeIntervalSince(loadedAt) < cacheTTL {
            return
        }

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load Discover.",
            rateLimitMessage: "LaughTrack is rate-limiting Discover right now.",
            undocumentedContext: "the Discover rail plan",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach Discover. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            sections = HomeDiscoverRailPlanPresentation.sections(from: feed)
            loadedRequestKey = requestKey
            loadedAt = Date()
        case .failure:
            // A plan is an enhancement over the established home experience;
            // transport failures keep the fixed sections instead of replacing
            // the whole screen with a second error surface.
            sections = nil
        }
    }
}
