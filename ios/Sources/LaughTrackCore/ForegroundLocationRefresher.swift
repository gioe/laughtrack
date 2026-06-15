import Foundation

/// Reports whether location access is already granted, *without* triggering an
/// authorization prompt. `ForegroundLocationRefresher` uses this to guarantee a
/// silent refresh never surprises the user with a permission dialog.
@MainActor
public protocol ForegroundLocationAuthorizing: AnyObject {
    var isLocationAuthorizedForForegroundRefresh: Bool { get }
}

/// Silently refreshes the stored nearby ZIP from the device's current location
/// when the app becomes active, so the server-side "comedian performing near
/// you" push job (`notify-comedian-arrivals`) targets the user's real location
/// instead of a ZIP frozen at their last manual location action.
///
/// Deliberately conservative — `refreshIfEligible()` is a no-op unless ALL hold:
/// - The saved preference came from geolocation (`source == .geolocated`). A
///   manually typed ZIP is an explicit choice we never silently override, and a
///   user who never tapped "use current location" is never quietly geolocated.
/// - Location is ALREADY authorized (when-in-use or always). It never triggers
///   a permission prompt — that escalation, if ever justified, is a separate
///   product decision.
///
/// It only writes (and PATCHes `/v1/me/location`) when the resolved ZIP actually
/// changed, so a stationary user costs zero writes and zero network calls.
@MainActor
public final class ForegroundLocationRefresher {
    private let store: NearbyPreferenceStore
    private let resolver: any NearbyLocationResolving
    private let authorization: (any ForegroundLocationAuthorizing)?
    private let syncClient: (any ProfileLocationPreferenceSyncing)?
    private var inFlight: Task<Void, Never>?

    public init(
        store: NearbyPreferenceStore,
        resolver: any NearbyLocationResolving,
        authorization: (any ForegroundLocationAuthorizing)?,
        syncClient: (any ProfileLocationPreferenceSyncing)?
    ) {
        self.store = store
        self.resolver = resolver
        self.authorization = authorization
        self.syncClient = syncClient
    }

    /// Starts a refresh if the eligibility gates pass. Returns the in-flight task
    /// (primarily so callers/tests can await it); returns `nil` when the refresh
    /// is skipped or one is already running.
    @discardableResult
    public func refreshIfEligible() -> Task<Void, Never>? {
        if let inFlight { return inFlight }

        guard let preference = store.preference, preference.source == .geolocated else { return nil }
        guard authorization?.isLocationAuthorizedForForegroundRefresh == true else { return nil }

        let task = Task { [weak self] in
            guard let self else { return }
            await self.performRefresh(previous: preference)
        }
        inFlight = task
        return task
    }

    private func performRefresh(previous: NearbyPreference) async {
        defer { inFlight = nil }

        guard let resolved = try? await resolver.requestCurrentLocation() else { return }
        guard let zipCode = NearbyPreferenceStore.validZip(from: resolved.zipCode) else { return }
        // Stationary user — nothing to persist or sync.
        guard zipCode != previous.zipCode else { return }

        guard let saved = store.setGeolocatedZip(
            zipCode,
            distanceMiles: previous.distanceMiles,
            city: resolved.city,
            state: resolved.state
        ) else { return }

        try? await syncClient?.setProfileLocation(
            zipCode: saved.zipCode,
            distanceMiles: saved.distanceMiles
        )
    }
}
