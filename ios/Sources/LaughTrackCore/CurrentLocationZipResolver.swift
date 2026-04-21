import CoreLocation
import Foundation

@MainActor
public final class CurrentLocationZipResolver: NSObject, NearbyLocationResolving {
    private let locationManager: CLLocationManager
    private let geocoder: CLGeocoder

    private var authorizationContinuation: CheckedContinuation<CLAuthorizationStatus, Never>?
    private var locationContinuation: CheckedContinuation<CLLocation, Error>?

    public init(
        locationManager: CLLocationManager = CLLocationManager(),
        geocoder: CLGeocoder = CLGeocoder()
    ) {
        self.locationManager = locationManager
        self.geocoder = geocoder
        super.init()
        self.locationManager.delegate = self
    }

    public func requestCurrentZip() async throws -> String {
        guard CLLocationManager.locationServicesEnabled() else {
            throw NearbyLocationError.servicesDisabled
        }

        let authorizationStatus = try await resolveAuthorizationStatus()
        switch authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            break
        case .denied:
            throw NearbyLocationError.denied
        case .restricted:
            throw NearbyLocationError.restricted
        case .notDetermined:
            throw NearbyLocationError.lookupFailed
        @unknown default:
            throw NearbyLocationError.lookupFailed
        }

        let location = try await requestLocation()
        let placemarks = try await geocoder.reverseGeocodeLocation(location)

        guard
            let postalCode = placemarks
                .compactMap(\.postalCode)
                .map({ String($0.filter(\.isNumber).prefix(5)) })
                .first(where: { $0.count == 5 })
        else {
            throw NearbyLocationError.zipUnavailable
        }

        return postalCode
    }

    private func resolveAuthorizationStatus() async throws -> CLAuthorizationStatus {
        switch locationManager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse, .denied, .restricted:
            return locationManager.authorizationStatus
        case .notDetermined:
            return await withCheckedContinuation { continuation in
                authorizationContinuation = continuation
                locationManager.requestWhenInUseAuthorization()
            }
        @unknown default:
            throw NearbyLocationError.lookupFailed
        }
    }

    private func requestLocation() async throws -> CLLocation {
        try await withCheckedThrowingContinuation { continuation in
            locationContinuation = continuation
            locationManager.requestLocation()
        }
    }

    private func finishAuthorization(with status: CLAuthorizationStatus) {
        authorizationContinuation?.resume(returning: status)
        authorizationContinuation = nil
    }

    private func finishLocation(with result: Result<CLLocation, Error>) {
        switch result {
        case .success(let location):
            locationContinuation?.resume(returning: location)
        case .failure(let error):
            locationContinuation?.resume(throwing: error)
        }
        locationContinuation = nil
    }
}

extension CurrentLocationZipResolver: @preconcurrency CLLocationManagerDelegate {
    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        guard status != .notDetermined else { return }

        finishAuthorization(with: status)

        if status == .denied {
            finishLocation(with: .failure(NearbyLocationError.denied))
        } else if status == .restricted {
            finishLocation(with: .failure(NearbyLocationError.restricted))
        }
    }

    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else {
            finishLocation(with: .failure(NearbyLocationError.unavailable))
            return
        }

        finishLocation(with: .success(location))
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if let clError = error as? CLError, clError.code == .denied {
            finishLocation(with: .failure(NearbyLocationError.denied))
        } else {
            finishLocation(with: .failure(NearbyLocationError.lookupFailed))
        }
    }
}
