import Foundation

/// Operation types that can be queued for offline execution.
public enum LaughTrackOfflineOperation: Hashable, Sendable {
    case toggleFavorite
    case setSavedShow(showId: Int)
}

extension LaughTrackOfflineOperation: Codable {
    private enum CodingKeys: String, CodingKey {
        case type
        case showId
    }

    private enum OperationType: String, Codable {
        case setSavedShow
    }

    public init(from decoder: Decoder) throws {
        if let legacyValue = try? decoder.singleValueContainer().decode(String.self) {
            guard legacyValue == "toggleFavorite" else {
                throw DecodingError.dataCorrupted(
                    .init(codingPath: decoder.codingPath, debugDescription: "Unknown offline operation")
                )
            }
            self = .toggleFavorite
            return
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        switch try container.decode(OperationType.self, forKey: .type) {
        case .setSavedShow:
            self = .setSavedShow(showId: try container.decode(Int.self, forKey: .showId))
        }
    }

    public func encode(to encoder: Encoder) throws {
        switch self {
        case .toggleFavorite:
            var container = encoder.singleValueContainer()
            try container.encode("toggleFavorite")
        case .setSavedShow(let showId):
            var container = encoder.container(keyedBy: CodingKeys.self)
            try container.encode(OperationType.setSavedShow, forKey: .type)
            try container.encode(showId, forKey: .showId)
        }
    }
}

/// Payload for the toggleFavorite operation.
public struct ToggleFavoritePayload: Codable, Sendable {
    public let comedianId: String
    public let isFavorite: Bool
}

/// Desired final state for an offline saved-show mutation.
public struct SavedShowMutationPayload: Codable, Sendable {
    public let showId: Int
    public let isSaved: Bool

    public init(showId: Int, isSaved: Bool) {
        self.showId = showId
        self.isSaved = isSaved
    }
}
