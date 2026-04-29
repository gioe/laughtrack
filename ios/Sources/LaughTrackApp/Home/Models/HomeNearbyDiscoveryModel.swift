import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeNearbyPage: Sendable {
    let items: [Components.Schemas.Show]
    let total: Int
    let zipCapTriggered: Bool
}

@MainActor
final class HomeNearbyDiscoveryModel: ObservableObject {
    @Published var zipCodeDraft = ""
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var phase: LoadPhase<HomeNearbyPage> = .idle
    @Published private(set) var zipValidationMessage: String?
    @Published private(set) var locationMessage: String?
    @Published private(set) var isEditingZip = false
    @Published private(set) var isResolvingLocation = false
    @Published private(set) var isPromptDismissed: Bool

    private let nearbyPreferenceStore: NearbyPreferenceStore
    private let appStateStorage: AppStateStorageProtocol
    private let nearbyLocationController: NearbyLocationController
    private var preferenceCancellable: AnyCancellable?
    private var locationStatusCancellable: AnyCancellable?
    private var locationLoadingCancellable: AnyCancellable?
    private var loadedPreference: NearbyPreference?
    private var loadedAt: Date?

    init(
        nearbyPreferenceStore: NearbyPreferenceStore,
        nearbyLocationController: NearbyLocationController,
        appStateStorage: AppStateStorageProtocol = AppStateStorage()
    ) {
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.appStateStorage = appStateStorage
        self.nearbyLocationController = nearbyLocationController
        self.isPromptDismissed = appStateStorage.getValue(
            forKey: StorageKey.promptDismissed,
            as: Bool.self
        ) ?? false
        self.activeNearbyPreference = nearbyPreferenceStore.preference
        self.zipCodeDraft = nearbyPreferenceStore.preference?.zipCode ?? ""

        preferenceCancellable = nearbyPreferenceStore.$preference
            .sink { [weak self] preference in
                self?.applyNearbyPreference(preference)
            }
        locationStatusCancellable = nearbyLocationController.$statusMessage
            .sink { [weak self] message in
                self?.locationMessage = message
            }
        locationLoadingCancellable = nearbyLocationController.$isResolvingCurrentLocation
            .sink { [weak self] isResolving in
                self?.isResolvingLocation = isResolving
            }
    }

    var requestKey: NearbyPreference? {
        activeNearbyPreference
    }

    var shouldShowPrompt: Bool {
        activeNearbyPreference == nil && !isPromptDismissed
    }

    func refresh(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        guard let preference = activeNearbyPreference else {
            loadedPreference = nil
            loadedAt = nil
            phase = .idle
            return
        }

        if loadedPreference == preference, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        let cacheKey = LaughTrackCacheKey.nearbyShows(
            zipCode: preference.zipCode,
            distanceMiles: preference.distanceMiles
        )
        if let cachedPage: HomeNearbyPage = await MainPageCache.get(cacheKey, from: cache) {
            apply(page: cachedPage, preference: preference)
            return
        }

        phase = .loading

        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: preference.zipCode,
                        from: nil,
                        to: nil,
                        page: 0,
                        size: 4,
                        comedian: nil,
                        club: nil,
                        distance: preference.distanceMiles,
                        sort: ShowSortOption.earliest.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let page = HomeNearbyPage(
                    items: response.data,
                    total: response.total,
                    zipCapTriggered: response.zipCapTriggered
                )
                await MainPageCache.set(page, forKey: cacheKey, in: cache, ttl: cacheTTL)
                apply(page: page, preference: preference)
            case .badRequest(let badRequest):
                phase = .failure(
                    .badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those nearby filters.")
                )
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                phase = .failure(
                    .rateLimited(retryAfter: retryAfter, message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting nearby shows right now.")
                )
            case .internalServerError(let serverError):
                phase = .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                phase = .failure(classifyUndocumented(status: status, context: "nearby shows"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .failure(
                .network("LaughTrack couldn't reach the nearby shows service. Check your connection and try again.")
            )
        }
    }

    func presentZipEntry() {
        setPromptDismissed(false)
        isEditingZip = true
        zipValidationMessage = nil
        locationMessage = nil
    }

    func dismissPrompt() {
        isEditingZip = false
        locationMessage = nil
        setPromptDismissed(true)
    }

    func clearNearby() {
        isEditingZip = false
        zipCodeDraft = ""
        loadedPreference = nil
        setPromptDismissed(false)
        nearbyLocationController.clear()
    }

    func applyManualZip() -> Bool {
        guard let preference = nearbyPreferenceStore.setManualZip(zipCodeDraft) else {
            zipValidationMessage = "Enter a valid 5-digit ZIP code to search nearby shows."
            return false
        }

        zipCodeDraft = preference.zipCode
        zipValidationMessage = nil
        locationMessage = nil
        isEditingZip = false
        return true
    }

    func useCurrentLocation() async {
        zipValidationMessage = nil
        let distanceMiles = activeNearbyPreference?.distanceMiles
            ?? NearbyPreference.defaultDistanceMiles
        let succeeded = await nearbyLocationController.useCurrentLocation(
            distanceMiles: distanceMiles
        )
        if succeeded {
            isEditingZip = false
        }
    }

    private func applyNearbyPreference(_ preference: NearbyPreference?) {
        activeNearbyPreference = preference
        zipValidationMessage = nil

        if let preference {
            zipCodeDraft = preference.zipCode
            loadedPreference = nil
            loadedAt = nil
            if isPromptDismissed {
                setPromptDismissed(false)
            }
        } else {
            loadedPreference = nil
            loadedAt = nil
            phase = .idle
            if !isEditingZip {
                zipCodeDraft = ""
            }
        }
    }

    private func apply(page: HomeNearbyPage, preference: NearbyPreference) {
        phase = .success(page)
        loadedPreference = preference
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private func setPromptDismissed(_ dismissed: Bool) {
        isPromptDismissed = dismissed
        appStateStorage.setValue(dismissed, forKey: StorageKey.promptDismissed)
    }

    private enum StorageKey {
        static let promptDismissed = "laughtrack.discovery.home-nearby-prompt-dismissed"
    }
}
