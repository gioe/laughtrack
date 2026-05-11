import Foundation
import LaughTrackAPIClient
import LaughTrackCore

func classifyDetailFetchError(_ error: Error, context: String) -> LoadFailure {
    guard let urlError = error as? URLError else {
        return .network("LaughTrack couldn't reach the \(context) service. Check your connection and try again.")
    }
    switch urlError.code {
    case .notConnectedToInternet:
        return .network("You appear to be offline. Check your connection and try again.")
    case .timedOut:
        return .network("LaughTrack timed out while loading \(context). Please try again.")
    case .cannotFindHost:
        return .network("LaughTrack couldn't find the \(context) service. Please try again in a moment.")
    default:
        return .network("LaughTrack couldn't reach the \(context) service. Check your connection and try again.")
    }
}

func isTransientDetailFetchError(_ error: URLError) -> Bool {
    switch error.code {
    case .timedOut,
         .cannotFindHost,
         .cannotConnectToHost,
         .dnsLookupFailed,
         .networkConnectionLost,
         .notConnectedToInternet:
        return true
    default:
        return false
    }
}

@MainActor
func withDetailFetchRetry<T>(
    backoff: Duration = .milliseconds(300),
    operation: @MainActor () async throws -> T
) async throws -> T {
    do {
        return try await operation()
    } catch let error as URLError where isTransientDetailFetchError(error) {
        try? await Task.sleep(for: backoff)
        return try await operation()
    }
}

@MainActor
final class ShowDetailModel: EntityDetailModel<Components.Schemas.ShowDetailResponse> {
    let showID: Int

    init(showID: Int) {
        self.showID = showID
    }

    func loadIfNeeded(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> Result<Components.Schemas.ShowDetailResponse, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getShow(.init(path: .init(id: showID)))
            }
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                for comedian in response.data.lineup ?? [] {
                    favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                }
                return .success(response)
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load this show right now."))
            case .notFound:
                return .failure(.unexpected(status: 404, message: "This show could not be found."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(retryAfter: retryAfter, message: "LaughTrack is rate-limiting show details right now."))
            case .internalServerError:
                return .failure(.serverError(status: 500, message: nil))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "show details"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "show details"))
        }
    }
}

struct ComedianDetailContent: Hashable {
    let comedian: Components.Schemas.ComedianDetail
    let upcomingShows: [Components.Schemas.Show]
    let upcomingShowsTotal: Int
    let relatedComedians: [Components.Schemas.ComedianLineup]
    let relatedContentMessage: String?
}

struct ClubDetailContent: Hashable {
    let club: Components.Schemas.ClubDetail
    let upcomingShows: [Components.Schemas.Show]
    let featuredComedians: [Components.Schemas.ComedianLineup]
    let relatedContentMessage: String?
}

@MainActor
final class ComedianDetailModel: EntityDetailModel<ComedianDetailContent> {
    private static let pageSize = 100
    let comedianID: Int
    @Published var fromDate: Date = Date()
    @Published var nearbyZipCode: String?
    @Published var nearbyDistanceMiles: Int?
    @Published private(set) var isRefetchingShows = false
    // Cached unfiltered total upcoming-show count. Set on the first call to
    // loadRelatedContent and reused for subsequent date-paged refetches —
    // the true comedian-wide total doesn't depend on the user's current week.
    private var cachedTotalUpcomingShows: Int?

    init(comedianID: Int) {
        self.comedianID = comedianID
    }

    func loadIfNeeded(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    func refreshUpcomingShows(apiClient: Client, favorites: ComedianFavoriteStore) async {
        guard case .success(let content) = phase else { return }
        isRefetchingShows = true
        defer { isRefetchingShows = false }

        let result = await loadRelatedContent(for: content.comedian, apiClient: apiClient, favorites: favorites)
        guard !Task.isCancelled else { return }
        if case .success(let updated) = result {
            // Preserve the initial "total upcoming from today" baseline across
            // date-paged refetches — the response.total for a future fromDate is
            // smaller and isn't the value we want to display.
            let merged = ComedianDetailContent(
                comedian: updated.comedian,
                upcomingShows: updated.upcomingShows,
                upcomingShowsTotal: content.upcomingShowsTotal,
                relatedComedians: updated.relatedComedians,
                relatedContentMessage: updated.relatedContentMessage
            )
            phase = .success(merged)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> Result<ComedianDetailContent, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getComedian(.init(path: .init(id: comedianID)))
            }
            switch output {
            case .ok(let ok):
                let comedian = try ok.body.json.data
                favorites.overwrite(uuid: comedian.uuid, value: favorites.value(for: comedian.uuid))
                return await loadRelatedContent(
                    for: comedian,
                    apiClient: apiClient,
                    favorites: favorites
                )
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load this comedian right now."))
            case .notFound:
                return .failure(.unexpected(status: 404, message: "This comedian could not be found."))
            case .internalServerError:
                return .failure(.serverError(status: 500, message: nil))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "comedian details"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "comedian details"))
        }
    }

    private func fetchTotalUpcomingShows(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client
    ) async -> Int? {
        if let cached = cachedTotalUpcomingShows { return cached }
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        from: ShowFormatting.apiDate(Date()),
                        page: 0,
                        size: 1,
                        comedian: comedian.name,
                        sort: ShowSortOption.earliest.rawValue
                    )
                )
            )
            if case .ok(let ok) = output, let parsed = try? ok.body.json {
                cachedTotalUpcomingShows = parsed.total
                return parsed.total
            }
        } catch {
            // Silent fallback — total is a UI nicety; not worth surfacing an error.
        }
        return nil
    }

    private func loadRelatedContent(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> Result<ComedianDetailContent, LoadFailure> {
        // Fire off the unfiltered-total request in parallel with the main fetch.
        async let totalUpcomingShowsTask = fetchTotalUpcomingShows(for: comedian, apiClient: apiClient)
        do {
            // Pass zip with max radius (500) so the API populates distanceMiles
            // for each show without filtering out the comedian's far-away tour stops.
            // The "near me" comparison is then done client-side against the user's
            // own radius preference.
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: nearbyZipCode,
                        from: ShowFormatting.apiDate(fromDate),
                        page: 0,
                        size: Self.pageSize,
                        comedian: comedian.name,
                        distance: nearbyZipCode == nil ? nil : 500,
                        sort: ShowSortOption.earliest.rawValue
                    )
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let relatedShows = response.data.filter { show in
                    guard let lineup = show.lineup else { return true }
                    return lineup.contains { lineupComedian in
                        lineupComedian.id == comedian.id || lineupComedian.uuid == comedian.uuid
                    }
                }

                for show in relatedShows {
                    for lineupComedian in show.lineup ?? [] {
                        favorites.seed(uuid: lineupComedian.uuid, value: lineupComedian.isFavorite)
                    }
                }

                // Rank related comedians by frequency: how often each one shares a bill
                // with the current comedian across the fetched related shows. Ties are
                // broken by first-seen order so output is deterministic.
                var counts: [String: Int] = [:]
                var firstSeen: [Components.Schemas.ComedianLineup] = []
                var seenUuids = Set<String>()
                for show in relatedShows {
                    for lineupComedian in show.lineup ?? [] {
                        guard
                            lineupComedian.id != comedian.id,
                            lineupComedian.uuid != comedian.uuid
                        else { continue }
                        counts[lineupComedian.uuid, default: 0] += 1
                        if seenUuids.insert(lineupComedian.uuid).inserted {
                            firstSeen.append(lineupComedian)
                        }
                    }
                }
                let relatedComedians = firstSeen
                    .enumerated()
                    .sorted { lhs, rhs in
                        let lc = counts[lhs.element.uuid] ?? 0
                        let rc = counts[rhs.element.uuid] ?? 0
                        if lc != rc { return lc > rc }
                        return lhs.offset < rhs.offset
                    }
                    .map(\.element)

                let totalUpcoming = await totalUpcomingShowsTask ?? response.total
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: relatedShows,
                        upcomingShowsTotal: totalUpcoming,
                        relatedComedians: relatedComedians,
                        relatedContentMessage: nil
                    )
                )
            case .badRequest:
                let totalUpcoming = await totalUpcomingShowsTask ?? 0
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        upcomingShowsTotal: totalUpcoming,
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack could not load the comedian's upcoming shows right now."
                    )
                )
            case .tooManyRequests:
                let totalUpcoming = await totalUpcomingShowsTask ?? 0
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        upcomingShowsTotal: totalUpcoming,
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack is rate-limiting related shows right now. Please try again in a moment."
                    )
                )
            case .internalServerError:
                let totalUpcoming = await totalUpcomingShowsTask ?? 0
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        upcomingShowsTotal: totalUpcoming,
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack hit a server error while loading related shows."
                    )
                )
            case .undocumented(let status, _):
                let totalUpcoming = await totalUpcomingShowsTask ?? 0
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        upcomingShowsTotal: totalUpcoming,
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status))."
                    )
                )
            }
        } catch {
            let totalUpcoming = await totalUpcomingShowsTask ?? 0
            return .success(
                .init(
                    comedian: comedian,
                    upcomingShows: [],
                    upcomingShowsTotal: totalUpcoming,
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack could not reach the related shows service. Check your connection and try again."
                )
            )
        }
    }
}

@MainActor
final class ClubDetailModel: EntityDetailModel<ClubDetailContent> {
    private static let pageSize = 60
    let clubID: Int
    @Published var fromDate: Date = Date()
    @Published private(set) var isRefetchingShows = false

    init(clubID: Int) {
        self.clubID = clubID
    }

    func loadIfNeeded(apiClient: Client) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient)
        }
    }

    func reload(apiClient: Client) async {
        await super.reload {
            await self.fetch(apiClient: apiClient)
        }
    }

    func refreshUpcomingShows(apiClient: Client) async {
        guard case .success(let content) = phase else { return }
        isRefetchingShows = true
        defer { isRefetchingShows = false }

        let result = await loadRelatedContent(for: content.club, apiClient: apiClient)
        guard !Task.isCancelled else { return }
        if case .success(let updated) = result {
            phase = .success(updated)
        }
    }

    private func fetch(apiClient: Client) async -> Result<ClubDetailContent, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getClub(.init(path: .init(id: clubID)))
            }
            switch output {
            case .ok(let ok):
                return await loadRelatedContent(for: try ok.body.json.data, apiClient: apiClient)
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load this club right now."))
            case .notFound:
                return .failure(.unexpected(status: 404, message: "This club could not be found."))
            case .internalServerError:
                return .failure(.serverError(status: 500, message: nil))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "club details"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "club details"))
        }
    }

    private func loadRelatedContent(
        for club: Components.Schemas.ClubDetail,
        apiClient: Client
    ) async -> Result<ClubDetailContent, LoadFailure> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        from: ShowFormatting.apiDate(fromDate),
                        page: 0,
                        size: Self.pageSize,
                        club: club.name,
                        sort: ShowSortOption.earliest.rawValue
                    )
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let upcomingShows = response.data.filter { show in
                    (show.clubName ?? "").localizedCaseInsensitiveCompare(club.name) == .orderedSame
                }

                var seenComedians = Set<String>()
                let featuredComedians = upcomingShows
                    .flatMap { $0.lineup ?? [] }
                    .filter { comedian in
                        seenComedians.insert(comedian.uuid).inserted
                    }

                return .success(
                    .init(
                        club: club,
                        upcomingShows: upcomingShows,
                        featuredComedians: featuredComedians,
                        relatedContentMessage: nil
                    )
                )
            case .badRequest:
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack could not load this club’s upcoming shows right now."
                    )
                )
            case .tooManyRequests:
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack is rate-limiting this club’s related content right now. Please try again in a moment."
                    )
                )
            case .internalServerError:
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack hit a server error while loading this club’s related content."
                    )
                )
            case .undocumented(let status, _):
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status))."
                    )
                )
            }
        } catch {
            return .success(
                .init(
                    club: club,
                    upcomingShows: [],
                    featuredComedians: [],
                    relatedContentMessage: "LaughTrack could not reach this club’s related content service. Check your connection and try again."
                )
            )
        }
    }
}
