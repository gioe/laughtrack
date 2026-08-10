import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class HomeTrendingPodcastsModel: ObservableObject {
    enum Content: Equatable {
        case episodes([Components.Schemas.HomeFeedPodcastEpisode])
        case legacyPodcasts([Components.Schemas.HomeFeedPodcast])
    }

    @Published private(set) var phase: LoadPhase<Content> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(
        for zipCode: String?,
        distanceMiles: Int? = nil,
        sessionDiscriminator: String? = nil
    ) -> String {
        "\(sessionDiscriminator ?? "signed-out")|\(HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles))"
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        sessionDiscriminator: String? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(
            for: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        let cachedFeed: Components.Schemas.HomeFeed? = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        )
        if let cachedFeed {
            apply(feed: cachedFeed, requestKey: requestKey)
        } else {
            phase = .loading
        }

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending podcasts.",
            rateLimitMessage: "LaughTrack is rate-limiting trending podcasts right now.",
            undocumentedContext: "trending podcasts",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending podcasts service. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            if cachedFeed == nil {
                phase = .failure(failure)
            }
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(Self.content(from: feed))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func content(from feed: Components.Schemas.HomeFeed) -> Content {
        if let episodes = feed.podcastEpisodes, !episodes.isEmpty {
            return .episodes(Array(episodes.prefix(HomeDiscoverRailPlanPresentation.itemLimit)))
        }
        return .legacyPodcasts(feed.trendingPodcasts)
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
