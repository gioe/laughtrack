import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class HomeShowsTonightModel: ObservableObject {
    static let displayLimit = 5

    static func seeMoreSearchSeed(
        railKind: HomeShowRailKind,
        nearbyPreference: NearbyPreference?
    ) -> SearchRootModel.Seed {
        SearchRootModel.Seed(
            pivot: .shows,
            query: "",
            shortcut: railKind.searchShortcut,
            nearbyPreference: nearbyPreference
        )
    }

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle
    @Published private(set) var cityTitle: String?
    @Published private(set) var feedNearbyPreference: NearbyPreference?

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(
        for zipCode: String?,
        distanceMiles: Int? = nil,
        railKind: HomeShowRailKind? = nil
    ) -> String {
        "\(railKind.map(String.init(describing:)) ?? "showsTonight")|\(HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles))"
    }

    func refresh(
        railKind: HomeShowRailKind = .showsTonight,
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles, railKind: railKind)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, railKind: railKind, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load tonight's shows.",
            rateLimitMessage: "LaughTrack is rate-limiting tonight's shows right now.",
            undocumentedContext: "tonight's shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the home feed. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, railKind: railKind, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind, requestKey: String) {
        cityTitle = Self.locationTitle(city: feed.hero.city, state: feed.hero.state)
        feedNearbyPreference = Self.nearbyPreference(from: feed.hero)
        phase = .success(Self.shows(from: feed, railKind: railKind))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private static func shows(from feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind) -> [Components.Schemas.Show] {
        let sourceShows: [Components.Schemas.Show]
        switch railKind {
        case .showsTonight:
            sourceShows = feed.showsTonight + feed.hero.shows + feed.trendingThisWeek
        case .thisWeek:
            let tonightIDs = Set((feed.showsTonight + feed.hero.shows).map(\.id))
            sourceShows = (feed.trendingThisWeek + feed.moreNearYou).filter { show in
                !tonightIDs.contains(show.id)
            }
        }

        var seenIDs: Set<Int> = []
        return sourceShows.filter { show in
            !ShowAvailability.isSoldOut(show) && seenIDs.insert(show.id).inserted
        }.prefix(Self.displayLimit).map { $0 }
    }

    private static func locationTitle(city: String?, state: String?) -> String? {
        guard let city, !city.isEmpty else { return nil }
        if let state, !state.isEmpty {
            return "\(city), \(state)"
        }
        return city
    }

    private static func nearbyPreference(from hero: Components.Schemas.HomeFeedHero) -> NearbyPreference? {
        guard let zipCode = hero.zipCode?.filter(\.isNumber), zipCode.count == 5 else {
            return nil
        }

        return NearbyPreference(
            zipCode: zipCode,
            source: .manual,
            distanceMiles: NearbyPreference.defaultDistanceMiles,
            city: hero.city,
            state: hero.state
        )
    }
}
