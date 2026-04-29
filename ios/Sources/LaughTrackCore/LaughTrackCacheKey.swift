import Foundation

/// App-specific cache key type for DataCache.
public enum LaughTrackCacheKey: Hashable, Sendable {
    case homeFeed(zipCode: String?)
    case favoriteShows(requestKey: String)
    case nearbyShows(zipCode: String, distanceMiles: Int)
    case showsSearch(requestKey: String, page: Int)
    case clubsSearch(query: String, page: Int)
    case comediansSearch(query: String, page: Int)
    case comedian(id: String)
    case club(id: String)
    case show(id: String)
}
