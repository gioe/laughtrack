import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class HomePopularClubsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ClubListItem]> = .idle

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
            badParamsMessage: "LaughTrack could not load clubs.",
            rateLimitMessage: "LaughTrack is rate-limiting clubs right now.",
            undocumentedContext: "clubs",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the clubs service. Check your connection and try again.",
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
        phase = .success(feed.popularClubs)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
