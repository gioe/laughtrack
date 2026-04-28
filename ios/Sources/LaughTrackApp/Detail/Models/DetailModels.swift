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
            let output = try await apiClient.getShow(.init(path: .init(id: showID)))
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
            return .failure(.network("LaughTrack couldn't reach the show details service. Check your connection and try again."))
        }
    }
}

struct ComedianDetailContent: Hashable {
    let comedian: Components.Schemas.ComedianDetail
    let upcomingShows: [Components.Schemas.Show]
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
    private static let pageSize = 8
    let comedianID: Int

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

    private func loadRelatedContent(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> Result<ComedianDetailContent, LoadFailure> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        from: ShowFormatting.apiDate(Date()),
                        page: 0,
                        size: Self.pageSize,
                        comedian: comedian.name,
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

                var seenRelatedComedians = Set<String>()
                let relatedComedians = relatedShows
                    .flatMap { $0.lineup ?? [] }
                    .filter { lineupComedian in
                        lineupComedian.id != comedian.id && lineupComedian.uuid != comedian.uuid
                    }
                    .filter { lineupComedian in
                        seenRelatedComedians.insert(lineupComedian.uuid).inserted
                    }

                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: relatedShows,
                        relatedComedians: relatedComedians,
                        relatedContentMessage: nil
                    )
                )
            case .badRequest:
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack could not load the comedian's upcoming shows right now."
                    )
                )
            case .tooManyRequests:
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack is rate-limiting related shows right now. Please try again in a moment."
                    )
                )
            case .internalServerError:
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack hit a server error while loading related shows."
                    )
                )
            case .undocumented(let status, _):
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status))."
                    )
                )
            }
        } catch {
            return .success(
                .init(
                    comedian: comedian,
                    upcomingShows: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack could not reach the related shows service. Check your connection and try again."
                )
            )
        }
    }
}

@MainActor
final class ClubDetailModel: EntityDetailModel<ClubDetailContent> {
    private static let pageSize = 8
    let clubID: Int

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
                        from: ShowFormatting.apiDate(Date()),
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
