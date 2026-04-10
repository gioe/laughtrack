import Foundation

/// Operation types that can be queued for offline execution.
public enum LaughTrackOfflineOperation: String, Codable, Hashable, Sendable {
    case toggleFavorite
}

/// Payload for the toggleFavorite operation.
public struct ToggleFavoritePayload: Codable, Sendable {
    public let comedianId: String
    public let isFavorite: Bool
}
