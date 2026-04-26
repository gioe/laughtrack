import Combine
import Foundation
import LaughTrackBridge
import SharedKit

public enum NearbyPreferenceSource: String, Codable, Equatable {
    case manual
    case geolocated
}

// City/state strategy (TASK-1793): the geolocation path harvests `locality` /
// `administrativeArea` from the same `CLPlacemark` that already produces the
// ZIP, so they cost nothing extra. The manual-ZIP path leaves them nil — we
// don't bundle a US ZIP→city dataset on iOS or call out to a network resolver,
// so manual-entry users see the static header until their next geolocation.
public struct NearbyPreference: Codable, Equatable {
    public let zipCode: String
    public let source: NearbyPreferenceSource
    public let distanceMiles: Int
    public let city: String?
    public let state: String?

    public init(
        zipCode: String,
        source: NearbyPreferenceSource,
        distanceMiles: Int = Self.defaultDistanceMiles,
        city: String? = nil,
        state: String? = nil
    ) {
        self.zipCode = NearbyPreferenceStore.normalize(zipCode)
        self.source = source
        self.distanceMiles = Self.normalize(distanceMiles)
        self.city = Self.sanitize(city)
        self.state = Self.sanitize(state)
    }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let zipCode = try container.decode(String.self, forKey: .zipCode)
        let source = try container.decode(NearbyPreferenceSource.self, forKey: .source)
        let savedDistanceMiles = try container.decodeIfPresent(Int.self, forKey: .distanceMiles)
        let legacyRadiusMiles = try container.decodeIfPresent(Int.self, forKey: .radiusMiles)
        let distanceMiles = savedDistanceMiles ?? legacyRadiusMiles ?? Self.defaultDistanceMiles
        let city = try container.decodeIfPresent(String.self, forKey: .city)
        let state = try container.decodeIfPresent(String.self, forKey: .state)

        self.init(zipCode: zipCode, source: source, distanceMiles: distanceMiles, city: city, state: state)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(zipCode, forKey: .zipCode)
        try container.encode(source, forKey: .source)
        try container.encode(distanceMiles, forKey: .distanceMiles)
        try container.encodeIfPresent(city, forKey: .city)
        try container.encodeIfPresent(state, forKey: .state)
    }

    private enum CodingKeys: String, CodingKey {
        case zipCode
        case source
        case distanceMiles
        case radiusMiles
        case city
        case state
    }

    public static let defaultDistanceMiles = 25

    private static func normalize(_ distanceMiles: Int) -> Int {
        max(1, distanceMiles)
    }

    private static func sanitize(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else {
            return nil
        }
        return trimmed
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
        distanceMiles: Int? = nil,
        city: String? = nil,
        state: String? = nil
    ) -> NearbyPreference? {
        guard let normalized = Self.validZip(from: zipCode) else { return nil }
        let preference = NearbyPreference(
            zipCode: normalized,
            source: .manual,
            distanceMiles: normalizedDistance(distanceMiles),
            city: city,
            state: state
        )
        setPreference(preference)
        return preference
    }

    @discardableResult
    public func setGeolocatedZip(
        _ zipCode: String,
        distanceMiles: Int? = nil,
        city: String? = nil,
        state: String? = nil
    ) -> NearbyPreference? {
        guard let normalized = Self.validZip(from: zipCode) else { return nil }
        let preference = NearbyPreference(
            zipCode: normalized,
            source: .geolocated,
            distanceMiles: normalizedDistance(distanceMiles),
            city: city,
            state: state
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
                distanceMiles: distanceMiles,
                city: preference.city,
                state: preference.state
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

@MainActor
public final class SettingsNearbyPreferenceModel: ObservableObject {
    public static let distanceOptions = [10, 25, 50, 100]

    @Published public var zipCodeDraft = ""
    @Published public var distanceMiles = NearbyPreference.defaultDistanceMiles
    @Published public private(set) var nearbyPreference: NearbyPreference?
    @Published public private(set) var validationMessage: String?

    private let nearbyPreferenceStore: NearbyPreferenceStore
    private var preferenceCancellable: AnyCancellable?

    public init(nearbyPreferenceStore: NearbyPreferenceStore) {
        self.nearbyPreferenceStore = nearbyPreferenceStore
        applyPreference(nearbyPreferenceStore.preference)
        preferenceCancellable = nearbyPreferenceStore.$preference
            .sink { [weak self] preference in
                self?.applyPreference(preference)
            }
    }

    public func saveNearbyPreference() {
        guard let preference = nearbyPreferenceStore.setManualZip(zipCodeDraft, distanceMiles: distanceMiles) else {
            validationMessage = "Enter a valid 5-digit ZIP code before saving this nearby preference."
            return
        }

        validationMessage = nil
        applyPreference(preference)
    }

    public func clearNearbyPreference() {
        validationMessage = nil
        nearbyPreferenceStore.clear()
    }

    private func applyPreference(_ preference: NearbyPreference?) {
        nearbyPreference = preference

        if let preference {
            zipCodeDraft = preference.zipCode
            distanceMiles = preference.distanceMiles
        } else {
            zipCodeDraft = ""
            distanceMiles = NearbyPreference.defaultDistanceMiles
        }
    }
}
