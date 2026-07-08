import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class HomeTrendingComediansModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ComedianListItem]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, distanceMiles: Int? = nil) -> String {
        HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles)
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending comedians.",
            rateLimitMessage: "LaughTrack is rate-limiting trending comedians right now.",
            undocumentedContext: "trending comedians",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending comedians service. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(Self.railItems(from: feed.trendingComedians))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func railItems(
        from comedians: [Components.Schemas.ComedianListItem]
    ) -> [Components.Schemas.ComedianListItem] {
        let photoBacked = comedians.filter(hasUsablePhoto)
        guard photoBacked.count >= 10 else {
            return photoBacked
        }

        let noPhoto = comedians.filter { !hasUsablePhoto($0) }
        return photoBacked + noPhoto
    }

    private static func hasUsablePhoto(_ comedian: Components.Schemas.ComedianListItem) -> Bool {
        let rawValue = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return URL.normalizedExternalURL(rawValue) != nil
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
