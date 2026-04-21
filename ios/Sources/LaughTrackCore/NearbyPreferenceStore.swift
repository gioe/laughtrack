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

    public init(zipCode: String, source: NearbyPreferenceSource) {
        self.zipCode = NearbyPreferenceStore.normalize(zipCode)
        self.source = source
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
    public func setManualZip(_ zipCode: String) -> NearbyPreference? {
        guard let normalized = Self.validZip(from: zipCode) else { return nil }
        let preference = NearbyPreference(zipCode: normalized, source: .manual)
        setPreference(preference)
        return preference
    }

    public func setGeolocatedZip(_ zipCode: String) {
        guard let normalized = Self.validZip(from: zipCode) else { return }
        setPreference(NearbyPreference(zipCode: normalized, source: .geolocated))
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

    private enum StorageKey {
        static let preference = "laughtrack.discovery.nearby-preference"
    }
}
