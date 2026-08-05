import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum MainPageCache {
    static let defaultTTL: TimeInterval = 60 * 60

    static func get<Value>(
        _ key: LaughTrackCacheKey,
        from cache: DataCache<LaughTrackCacheKey>?,
        persistentCache: PersistentMainPageCache?
    ) async -> Value? {
        if let cached: Value = await cache?.get(forKey: key) {
            if let homeFeed = cached as? Components.Schemas.HomeFeed {
                return homeFeed.publicCacheSlice as? Value
            }
            return cached
        }

        guard let persistentCache else {
            return nil
        }

        switch key {
        case .homeFeed(let zipCode, let distanceMiles) where Value.self == Components.Schemas.HomeFeed.self:
            guard let cached = await persistentCache.getCachedHomeFeed(
                zipCode: zipCode,
                distanceMiles: distanceMiles
            ) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        case .favoriteShows(let requestKey) where Value.self == [Components.Schemas.Show].self:
            guard let cached = await persistentCache.getCachedFavoriteShows(requestKey: requestKey) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        default:
            return nil
        }
    }

    static func set(
        _ value: some Sendable,
        forKey key: LaughTrackCacheKey,
        in cache: DataCache<LaughTrackCacheKey>?,
        ttl: TimeInterval = defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        switch key {
        case .homeFeed(let zipCode, let distanceMiles):
            guard let homeFeed = value as? Components.Schemas.HomeFeed else { return }
            let publicFeed = homeFeed.publicCacheSlice
            await cache?.set(publicFeed, forKey: key, ttl: ttl)
            await persistentCache?.setHomeFeed(
                publicFeed,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                ttl: ttl
            )
        case .favoriteShows(let requestKey):
            await cache?.set(value, forKey: key, ttl: ttl)
            guard let shows = value as? [Components.Schemas.Show] else { return }
            await persistentCache?.setFavoriteShows(shows, requestKey: requestKey, ttl: ttl)
        default:
            await cache?.set(value, forKey: key, ttl: ttl)
        }
    }

    private static func hydrateMemoryCache(
        _ value: some Sendable,
        key: LaughTrackCacheKey,
        expiresAt: Date,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        await cache?.set(value, forKey: key, ttl: max(0, expiresAt.timeIntervalSinceNow))
    }
}
