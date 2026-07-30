import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
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
        await loadIfNeeded(apiClient: apiClient, favorites: favorites, cache: nil)
    }

    func loadIfNeeded(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        if case .idle = phase,
           let cached: Components.Schemas.ShowDetailResponse = await MainPageCache.get(
            .show(id: String(showID)),
            from: cache,
            persistentCache: nil
           ) {
            seedFavorites(from: cached, favorites: favorites)
            phase = .success(cached)
            return
        }

        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites, cache: cache)
        }
    }

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await reload(apiClient: apiClient, favorites: favorites, cache: nil)
    }

    func reload(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites, cache: cache)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async -> Result<Components.Schemas.ShowDetailResponse, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getShow(.init(path: .init(id: showID)))
            }
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                seedFavorites(from: response, favorites: favorites)
                await MainPageCache.set(response, forKey: .show(id: String(showID)), in: cache, persistentCache: nil)
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

    private func seedFavorites(
        from response: Components.Schemas.ShowDetailResponse,
        favorites: ComedianFavoriteStore
    ) {
        for comedian in response.data.lineup ?? [] {
            favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
        }
    }
}

struct ComedianDetailContent: Hashable {
    let comedian: Components.Schemas.ComedianDetail
    let upcomingRuns: [Components.Schemas.UpcomingRun]
    let relatedComedians: [Components.Schemas.ComedianLineup]
    let relatedContentMessage: String?
}

struct ComedianPastShowsPage: Hashable {
    let shows: [Components.Schemas.Show]
    let total: Int
    let page: Int

    var canLoadMore: Bool { shows.count < total }
}

struct ClubDetailContent: Hashable {
    let club: Components.Schemas.ClubDetail
}

@MainActor
final class ComedianDetailModel: EntityDetailModel<ComedianDetailContent> {
    static let pastShowsPageSize = 20

    let comedianID: Int

    @Published private(set) var pastShowsPhase: LoadPhase<ComedianPastShowsPage> = .idle
    @Published private(set) var isLoadingMorePastShows = false
    @Published private(set) var pastShowsPaginationFailure: LoadFailure?

    init(comedianID: Int) {
        self.comedianID = comedianID
    }

    func loadIfNeeded(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        await loadIfNeeded(apiClient: apiClient, favorites: favorites, cache: nil)
    }

    func loadIfNeeded(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        if case .idle = phase,
           let cached: ComedianDetailContent = await MainPageCache.get(
            .comedian(id: String(comedianID)),
            from: cache,
            persistentCache: nil
           ) {
            seedFavorites(from: cached, favorites: favorites)
            phase = .success(cached)
            return
        }

        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites, cache: cache)
        }
    }

    func reload(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        await reload(apiClient: apiClient, favorites: favorites, cache: nil)
    }

    func reload(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites, cache: cache)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
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
                    favorites: favorites,
                    cache: cache
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

    private func loadRelatedContent(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?
    ) async -> Result<ComedianDetailContent, LoadFailure> {
        do {
            let output = try await apiClient.getComedianUpcomingRuns(
                .init(
                    path: .init(id: comedian.id),
                    query: .init(club: nil, location: nil, date: nil),
                    headers: .init(xTimezone: TimeZone.current.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json

                for show in response.data.flatMap(\.shows) {
                    for lineupComedian in show.lineup ?? [] {
                        favorites.seed(uuid: lineupComedian.uuid, value: lineupComedian.isFavorite)
                    }
                }

                let (relatedComedians, coBillMessage) = await loadCoBilledComedians(
                    for: comedian,
                    apiClient: apiClient,
                    favorites: favorites
                )

                let content = ComedianDetailContent(
                    comedian: comedian,
                    upcomingRuns: response.data,
                    relatedComedians: relatedComedians,
                    relatedContentMessage: coBillMessage
                )
                if coBillMessage == nil {
                    await MainPageCache.set(content, forKey: .comedian(id: String(comedianID)), in: cache, persistentCache: nil)
                }
                return .success(content)
            case .badRequest:
                return await cacheAndReturn(
                    comedian: comedian,
                    upcomingRuns: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack could not load the comedian's upcoming shows right now.",
                    cache: cache
                )
            case .tooManyRequests:
                return await cacheAndReturn(
                    comedian: comedian,
                    upcomingRuns: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack is rate-limiting related shows right now. Please try again in a moment.",
                    cache: cache
                )
            case .internalServerError:
                return await cacheAndReturn(
                    comedian: comedian,
                    upcomingRuns: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack hit a server error while loading related shows.",
                    cache: cache
                )
            case .undocumented(let status, _):
                return await cacheAndReturn(
                    comedian: comedian,
                    upcomingRuns: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status)).",
                    cache: cache
                )
            }
        } catch {
            return await cacheAndReturn(
                comedian: comedian,
                upcomingRuns: [],
                relatedComedians: [],
                relatedContentMessage: "LaughTrack could not reach the related shows service. Check your connection and try again.",
                cache: cache
            )
        }
    }

    private func cacheAndReturn(
        comedian: Components.Schemas.ComedianDetail,
        upcomingRuns: [Components.Schemas.UpcomingRun],
        relatedComedians: [Components.Schemas.ComedianLineup],
        relatedContentMessage: String?,
        cache: DataCache<LaughTrackCacheKey>?
    ) async -> Result<ComedianDetailContent, LoadFailure> {
        let content = ComedianDetailContent(
            comedian: comedian,
            upcomingRuns: upcomingRuns,
            relatedComedians: relatedComedians,
            relatedContentMessage: relatedContentMessage
        )
        if relatedContentMessage == nil {
            await MainPageCache.set(content, forKey: .comedian(id: String(comedianID)), in: cache, persistentCache: nil)
        }
        return .success(content)
    }

    private func seedFavorites(
        from content: ComedianDetailContent,
        favorites: ComedianFavoriteStore
    ) {
        for show in content.upcomingRuns.flatMap(\.shows) {
            for comedian in show.lineup ?? [] {
                favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
            }
        }

        for comedian in content.relatedComedians {
            favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
        }
    }

    func loadPastShowsIfNeeded(apiClient: Client, comedianName: String) async {
        guard case .idle = pastShowsPhase else { return }
        await reloadPastShows(apiClient: apiClient, comedianName: comedianName)
    }

    func reloadPastShows(apiClient: Client, comedianName: String) async {
        pastShowsPhase = .loading
        pastShowsPaginationFailure = nil
        let result = await fetchPastShows(
            apiClient: apiClient,
            comedianName: comedianName,
            page: 0
        )
        guard !Task.isCancelled else { return }
        switch result {
        case .success(let payload):
            pastShowsPhase = .success(.init(
                shows: payload.data,
                total: payload.total,
                page: 0
            ))
        case .failure(let failure):
            pastShowsPhase = .failure(failure)
        }
    }

    func loadMorePastShows(apiClient: Client, comedianName: String) async {
        guard case .success(let current) = pastShowsPhase,
              current.canLoadMore,
              !isLoadingMorePastShows
        else { return }

        isLoadingMorePastShows = true
        pastShowsPaginationFailure = nil
        defer { isLoadingMorePastShows = false }

        let nextPage = current.page + 1
        let result = await fetchPastShows(
            apiClient: apiClient,
            comedianName: comedianName,
            page: nextPage
        )
        guard !Task.isCancelled else { return }
        switch result {
        case .success(let payload):
            pastShowsPhase = .success(.init(
                shows: current.shows + payload.data,
                total: payload.total,
                page: nextPage
            ))
        case .failure(let failure):
            pastShowsPaginationFailure = failure
        }
    }

    private func fetchPastShows(
        apiClient: Client,
        comedianName: String,
        page: Int
    ) async -> Result<(data: [Components.Schemas.Show], total: Int), LoadFailure> {
        do {
            let output = try await apiClient.getComedianPastShows(
                .init(
                    query: .init(
                        comedian: comedianName,
                        page: page,
                        size: Self.pastShowsPageSize
                    ),
                    headers: .init(xTimezone: TimeZone.current.identifier)
                )
            )
            switch output {
            case .ok(let ok):
                let payload = try ok.body.json
                return .success((data: payload.data, total: payload.total))
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load past shows right now."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(
                    retryAfter: retryAfter,
                    message: "LaughTrack is rate-limiting past shows right now."
                ))
            case .internalServerError:
                return .failure(.serverError(status: 500, message: nil))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "past shows"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "past shows"))
        }
    }

    private func loadCoBilledComedians(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> ([Components.Schemas.ComedianLineup], String?) {
        do {
            // Uses /comedians/{id}/co-bill so solo headliners get historical overlap.
            let output = try await apiClient.getComedianCoBill(
                .init(path: .init(id: comedian.id))
            )

            switch output {
            case .ok(let ok):
                let comedians = try ok.body.json.data
                for comedian in comedians {
                    favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                }
                return (comedians, nil)
            case .badRequest:
                return ([], "LaughTrack could not load related comedians right now.")
            case .tooManyRequests:
                return ([], "LaughTrack is rate-limiting related comedians right now. Please try again in a moment.")
            case .internalServerError:
                return ([], "LaughTrack hit a server error while loading related comedians.")
            case .undocumented(let status, _):
                return ([], "LaughTrack returned an unexpected related comedians response (\(status)).")
            }
        } catch {
            return ([], "LaughTrack could not reach the related comedians service. Check your connection and try again.")
        }
    }
}

@MainActor
final class ClubDetailModel: EntityDetailModel<ClubDetailContent> {
    let clubId: Int

    init(clubId: Int) {
        self.clubId = clubId
    }

    func loadIfNeeded(apiClient: Client) async {
        await loadIfNeeded(apiClient: apiClient, cache: nil)
    }

    func loadIfNeeded(apiClient: Client, cache: DataCache<LaughTrackCacheKey>?) async {
        if case .idle = phase,
           let cached: ClubDetailContent = await MainPageCache.get(
            .club(id: String(clubId)),
            from: cache,
            persistentCache: nil
           ) {
            phase = .success(cached)
            return
        }

        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, cache: cache)
        }
    }

    func reload(apiClient: Client) async {
        await reload(apiClient: apiClient, cache: nil)
    }

    func reload(apiClient: Client, cache: DataCache<LaughTrackCacheKey>?) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, cache: cache)
        }
    }

    private func fetch(apiClient: Client, cache: DataCache<LaughTrackCacheKey>?) async -> Result<ClubDetailContent, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getClub(.init(path: .init(id: clubId)))
            }
            switch output {
            case .ok(let ok):
                let content = ClubDetailContent(club: try ok.body.json.data)
                await MainPageCache.set(
                    content,
                    forKey: .club(id: String(clubId)),
                    in: cache,
                    persistentCache: nil
                )
                return .success(content)
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
}

@MainActor
final class ClubHighlightsModel: EntityDetailModel<Components.Schemas.ClubHighlights> {
    let clubId: Int

    init(clubId: Int) {
        self.clubId = clubId
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

    private func fetch(apiClient: Client) async -> Result<Components.Schemas.ClubHighlights, LoadFailure> {
        do {
            let output = try await withDetailFetchRetry {
                try await apiClient.getClubHighlights(.init(path: .init(id: clubId)))
            }

            switch output {
            case .ok(let ok):
                return .success(try ok.body.json.data)
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load this club’s highlights right now."))
            case .notFound:
                return .failure(.unexpected(status: 404, message: "Club highlights could not be found."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(
                    retryAfter: retryAfter,
                    message: "LaughTrack is rate-limiting club highlights right now."
                ))
            case .internalServerError:
                return .failure(.serverError(status: 500, message: nil))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "club highlights"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "club highlights"))
        }
    }
}
