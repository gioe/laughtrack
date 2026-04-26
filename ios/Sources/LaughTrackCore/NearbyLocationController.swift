import Combine
import Foundation

public enum NearbyLocationError: Error, Equatable {
    case servicesDisabled
    case denied
    case restricted
    case unavailable
    case zipUnavailable
    case lookupFailed

    public var recoveryMessage: String {
        switch self {
        case .servicesDisabled, .unavailable:
            return "Current location is unavailable on this device. Enter a ZIP manually to keep browsing."
        case .denied:
            return "Location access is turned off for LaughTrack. Enter a ZIP manually or enable location in Settings."
        case .restricted:
            return "This device cannot share location right now. Enter a ZIP manually to keep browsing."
        case .zipUnavailable:
            return "LaughTrack found your location but could not match it to a 5-digit ZIP code. Enter one manually to keep browsing."
        case .lookupFailed:
            return "LaughTrack could not determine your current location. Enter a ZIP manually or try again."
        }
    }
}

public struct ResolvedNearbyLocation: Equatable {
    public let zipCode: String
    public let city: String?
    public let state: String?

    public init(zipCode: String, city: String? = nil, state: String? = nil) {
        self.zipCode = zipCode
        self.city = city
        self.state = state
    }
}

@MainActor
public protocol NearbyLocationResolving: AnyObject {
    func requestCurrentZip() async throws -> String
    func requestCurrentLocation() async throws -> ResolvedNearbyLocation
}

extension NearbyLocationResolving {
    public func requestCurrentLocation() async throws -> ResolvedNearbyLocation {
        ResolvedNearbyLocation(zipCode: try await requestCurrentZip())
    }
}

@MainActor
public final class NearbyLocationController: ObservableObject {
    @Published public private(set) var preference: NearbyPreference?
    @Published public private(set) var statusMessage: String?
    @Published public private(set) var isResolvingCurrentLocation = false

    public private(set) var pendingZipRefinement: Task<Void, Never>?

    private let store: NearbyPreferenceStore
    private let resolver: NearbyLocationResolving
    private let zipLocationResolver: any ZipLocationResolving
    private var preferenceCancellable: AnyCancellable?

    public init(
        store: NearbyPreferenceStore,
        resolver: NearbyLocationResolving,
        zipLocationResolver: any ZipLocationResolving
    ) {
        self.store = store
        self.resolver = resolver
        self.zipLocationResolver = zipLocationResolver
        self.preference = store.preference
        preferenceCancellable = store.$preference
            .sink { [weak self] preference in
                self?.preference = preference
            }
    }

    @discardableResult
    public func applyManualZip(_ zipCode: String, distanceMiles: Int) -> Bool {
        guard let saved = store.setManualZip(zipCode, distanceMiles: distanceMiles) else {
            statusMessage = "Enter a valid 5-digit ZIP code to search nearby shows."
            return false
        }

        statusMessage = nil
        pendingZipRefinement?.cancel()
        pendingZipRefinement = Task { [weak self] in
            await self?.refineManualZipLocation(baseline: saved)
        }
        return true
    }

    private func refineManualZipLocation(baseline: NearbyPreference) async {
        guard
            let resolved = try? await zipLocationResolver.resolveLocation(forZip: baseline.zipCode),
            let city = resolved.city, !city.isEmpty
        else {
            return
        }
        // Only update if the user hasn't moved on (different ZIP, geolocation, or cleared).
        guard
            let current = store.preference,
            current.zipCode == baseline.zipCode,
            current.source == .manual
        else {
            return
        }
        _ = store.setManualZip(
            current.zipCode,
            distanceMiles: current.distanceMiles,
            city: resolved.city,
            state: resolved.state
        )
    }

    public func clear() {
        statusMessage = nil
        pendingZipRefinement?.cancel()
        pendingZipRefinement = nil
        store.clear()
    }

    public func updateDistanceMiles(_ distanceMiles: Int) {
        store.setDistance(distanceMiles)
    }

    @discardableResult
    public func useCurrentLocation(distanceMiles: Int) async -> Bool {
        statusMessage = nil
        isResolvingCurrentLocation = true
        defer { isResolvingCurrentLocation = false }

        do {
            let resolved = try await resolver.requestCurrentLocation()
            guard
                store.setGeolocatedZip(
                    resolved.zipCode,
                    distanceMiles: distanceMiles,
                    city: resolved.city,
                    state: resolved.state
                ) != nil
            else {
                statusMessage = NearbyLocationError.zipUnavailable.recoveryMessage
                return false
            }
            statusMessage = nil
            return true
        } catch let error as NearbyLocationError {
            statusMessage = error.recoveryMessage
            return false
        } catch {
            statusMessage = NearbyLocationError.lookupFailed.recoveryMessage
            return false
        }
    }
}
