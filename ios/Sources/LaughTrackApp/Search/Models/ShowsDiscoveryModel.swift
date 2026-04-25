import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackCore

@MainActor
final class ShowsDiscoveryModel: EntitySearchModel<ShowsDiscoveryQuery, Components.Schemas.Show>, SearchRootQueryReceivable {
    private static let pageSize = 10

    @Published var zipCodeDraft = ""
    @Published var comedianSearchText = ""
    @Published var clubSearchText = ""
    @Published var useDateRange = false
    @Published var fromDate = Calendar.current.startOfDay(for: Date())
    @Published var toDate = Calendar.current.date(byAdding: .day, value: 14, to: Calendar.current.startOfDay(for: Date())) ?? Date()
    @Published var distance: ShowDistanceOption = .city {
        didSet {
            guard let activeNearbyPreference, activeNearbyPreference.distanceMiles != distance.rawValue else { return }
            nearbyLocationController.updateDistanceMiles(distance.rawValue)
        }
    }
    @Published var sort: ShowSortOption = .earliest
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var nearbyStatusMessage: String?
    @Published private(set) var zipCapTriggered = false
    @Published private(set) var isResolvingCurrentLocation = false

    private let nearbyLocationController: NearbyLocationController
    private var nearbyPreferenceCancellable: AnyCancellable?
    private var nearbyStatusCancellable: AnyCancellable?
    private var nearbyLoadingCancellable: AnyCancellable?
    init(nearbyLocationController: NearbyLocationController) {
        self.nearbyLocationController = nearbyLocationController
        super.init()
        applyNearbyPreference(nearbyLocationController.preference)
        nearbyPreferenceCancellable = nearbyLocationController.$preference
            .sink { [weak self] preference in
                self?.applyNearbyPreference(preference)
            }
        nearbyStatusCancellable = nearbyLocationController.$statusMessage
            .sink { [weak self] message in
                self?.nearbyStatusMessage = message
            }
        nearbyLoadingCancellable = nearbyLocationController.$isResolvingCurrentLocation
            .sink { [weak self] isResolving in
                self?.isResolvingCurrentLocation = isResolving
            }
    }

    var requestKey: ShowsDiscoveryQuery {
        let trimmedTo = max(toDate, fromDate)
        return .init(
            comedian: comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            club: clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            zip: activeNearbyPreference?.zipCode ?? "",
            useDateRange: useDateRange,
            from: fromDate,
            to: trimmedTo,
            distance: distance,
            sort: sort
        )
    }

    var timezoneLabel: String {
        let timezone = TimeZone.autoupdatingCurrent
        return timezone.localizedName(for: .shortStandard, locale: .current) ?? timezone.identifier
    }

    func reload(apiClient: Client) async {
        let query = requestKey
        await super.reload(query: query, shouldDebounce: query.hasActiveFilters) { [weak self] page, query in
            guard let self else { return .failure(.unexpected(status: 0, message: "LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func loadMore(apiClient: Client) async {
        await super.loadMore(query: requestKey) { [weak self] page, query in
            guard let self else { return .failure(.unexpected(status: 0, message: "LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func applySearchRootQuery(_ query: String) {
        // The unified root currently treats show search as a comedian-name query.
        // Venue-name discovery remains explicit in the Clubs pivot.
        comedianSearchText = query
        clubSearchText = ""
    }

    func clearLocation() {
        zipCodeDraft = ""
        nearbyStatusMessage = nil
        nearbyLocationController.clear()
    }

    func applyManualZip() -> Bool {
        guard !zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            clearLocation()
            return true
        }

        return nearbyLocationController.applyManualZip(zipCodeDraft, distanceMiles: distance.rawValue)
    }

    @discardableResult
    func useCurrentLocation() async -> Bool {
        await nearbyLocationController.useCurrentLocation(distanceMiles: distance.rawValue)
    }

    private func fetchPage(
        page: Int,
        query: ShowsDiscoveryQuery,
        apiClient: Client
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.Show>, LoadFailure> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: query.sanitizedZip,
                        from: query.fromString,
                        to: query.toString,
                        page: page,
                        size: Self.pageSize,
                        comedian: query.comedian.nonEmpty,
                        club: query.club.nonEmpty,
                        distance: query.sanitizedZip == nil ? nil : query.distance.rawValue,
                        sort: query.sort.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                zipCapTriggered = response.zipCapTriggered
                return .success(
                    .init(
                        items: response.data,
                        total: response.total
                    )
                )
            case .badRequest(let badRequest):
                return .failure(.badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those show filters."))
            case .internalServerError(let serverError):
                return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "shows"))
            }
        } catch {
            return .failure(.network("LaughTrack couldn't reach the shows search service. Check your connection and try again."))
        }
    }

    private func applyNearbyPreference(_ preference: NearbyPreference?) {
        activeNearbyPreference = preference

        if let preference {
            zipCodeDraft = preference.zipCode
            distance = .from(distanceMiles: preference.distanceMiles)
        } else if zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            zipCodeDraft = ""
            distance = .city
        }
    }
}
