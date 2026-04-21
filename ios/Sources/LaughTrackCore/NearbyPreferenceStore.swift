import Combine
import Foundation
import LaughTrackBridge
import SharedKit

public enum NearbyPreferenceSource: String, Codable, Equatable {
    case manual
    case geolocated
}

public struct NearbyPreference: Codable, Equatable {
    public let zipCode: String
    public let source: NearbyPreferenceSource
    public let distanceMiles: Int

    public init(
        zipCode: String,
        source: NearbyPreferenceSource,
        distanceMiles: Int = Self.defaultDistanceMiles
    ) {
        self.zipCode = NearbyPreferenceStore.normalize(zipCode)
        self.source = source
        self.distanceMiles = Self.normalize(distanceMiles)
    }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let zipCode = try container.decode(String.self, forKey: .zipCode)
        let source = try container.decode(NearbyPreferenceSource.self, forKey: .source)
        let savedDistanceMiles = try container.decodeIfPresent(Int.self, forKey: .distanceMiles)
        let legacyRadiusMiles = try container.decodeIfPresent(Int.self, forKey: .radiusMiles)
        let distanceMiles = savedDistanceMiles ?? legacyRadiusMiles ?? Self.defaultDistanceMiles

        self.init(zipCode: zipCode, source: source, distanceMiles: distanceMiles)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(zipCode, forKey: .zipCode)
        try container.encode(source, forKey: .source)
        try container.encode(distanceMiles, forKey: .distanceMiles)
    }

    private enum CodingKeys: String, CodingKey {
        case zipCode
        case source
        case distanceMiles
        case radiusMiles
    }

    public static let defaultDistanceMiles = 25

    private static func normalize(_ distanceMiles: Int) -> Int {
        max(1, distanceMiles)
    }
}

@MainActor
public final class NearbyPreferenceStore: ObservableObject {
    @Published public private(set) var preference: NearbyPreference?

    private let appStateStorage: AppStateStorageProtocol

    public convenience init() {
        self.init(appStateStorage: AppStateStorage())
    }

    public init(appStateStorage: AppStateStorageProtocol) {
        self.appStateStorage = appStateStorage
        self.preference = appStateStorage.getValue(
            forKey: StorageKey.preference,
            as: NearbyPreference.self
        )
    }

    @discardableResult
    public func setManualZip(
        _ zipCode: String,
        distanceMiles: Int? = nil
    ) -> NearbyPreference? {
        guard let normalized = Self.validZip(from: zipCode) else { return nil }
        let preference = NearbyPreference(
            zipCode: normalized,
            source: .manual,
            distanceMiles: normalizedDistance(distanceMiles)
        )
        setPreference(preference)
        return preference
    }

    @discardableResult
    public func setGeolocatedZip(
        _ zipCode: String,
        distanceMiles: Int? = nil
    ) -> NearbyPreference? {
        guard let normalized = Self.validZip(from: zipCode) else { return nil }
        let preference = NearbyPreference(
            zipCode: normalized,
            source: .geolocated,
            distanceMiles: normalizedDistance(distanceMiles)
        )
        setPreference(preference)
        return preference
    }

    public func setDistance(_ distanceMiles: Int) {
        guard let preference else { return }

        setPreference(
            NearbyPreference(
                zipCode: preference.zipCode,
                source: preference.source,
                distanceMiles: distanceMiles
            )
        )
    }

    public func clear() {
        preference = nil
        appStateStorage.removeValue(forKey: StorageKey.preference)
    }

    public nonisolated static func validZip(from zipCode: String) -> String? {
        let normalized = normalize(zipCode)
        guard normalized.count == 5 else { return nil }
        return normalized
    }

    public nonisolated static func normalize(_ zipCode: String) -> String {
        String(zipCode.filter(\.isNumber).prefix(5))
    }

    private func setPreference(_ preference: NearbyPreference) {
        self.preference = preference
        appStateStorage.setValue(preference, forKey: StorageKey.preference)
    }

    private func normalizedDistance(_ distanceMiles: Int?) -> Int {
        max(1, distanceMiles ?? preference?.distanceMiles ?? NearbyPreference.defaultDistanceMiles)
    }

    private enum StorageKey {
        static let preference = "laughtrack.discovery.nearby-preference"
    }
}
