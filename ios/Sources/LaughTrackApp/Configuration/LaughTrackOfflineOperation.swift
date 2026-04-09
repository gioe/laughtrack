import Foundation

/// Operation types that can be queued for offline execution.
enum LaughTrackOfflineOperation: String, Codable, Hashable, Sendable {
    case toggleFavorite
}

/// Payload for the toggleFavorite operation.
struct ToggleFavoritePayload: Codable, Sendable {
    let comedianId: String
    let isFavorite: Bool
}
