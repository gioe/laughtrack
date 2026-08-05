import Foundation

/// App-specific cache key type for DataCache.
public enum LaughTrackCacheKey: Hashable, Sendable {
    /// Location-scoped public home-feed rails. Personalized sections must not
    /// be stored under this key because it is intentionally reusable across
    /// anonymous and authenticated sessions.
    case homeFeed(zipCode: String?, distanceMiles: Int?)
    case favoriteShows(requestKey: String)
    case savedShowState(accountId: String, showId: Int)
    case savedShows(accountId: String, period: String, page: Int, size: Int)
    case showsSearch(requestKey: String, page: Int)
    case clubsSearch(query: String, page: Int)
    case comediansSearch(query: String, page: Int)
    case comedian(id: String)
    case club(id: String)
    case show(id: String)
    case podcast(id: String)
}
