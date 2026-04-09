import Foundation

/// App-specific cache key type for DataCache.
enum LaughTrackCacheKey: Hashable, Sendable {
    case comedian(id: String)
    case club(id: String)
    case show(id: String)
}
