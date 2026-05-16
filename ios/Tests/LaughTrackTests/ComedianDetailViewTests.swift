import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Comedian detail view")
@MainActor
struct ComedianDetailViewTests {
    @Test("comedian detail loads live profile and related content")
    func comedianDetailLoadsAndDisplaysSections() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let favorites = ComedianFavoriteStore()
        await model.loadIfNeeded(
            apiClient: makeClient(
                comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                upcomingRunsResponse: .success(
                    .init(
                        data: [
                            fallbackRun(showIDs: [301])
                        ]
                    )
                ),
                coBillResponse: .success(
                    .init(data: [fallbackRelatedComedian()])
                )
            ),
            favorites: favorites
        )

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }

        #expect(content.comedian.name == "Mark Normand")
        #expect(content.upcomingRuns.count == 1)
        #expect(content.upcomingRuns.first?.shows.map(\.id) == [301])
        #expect(content.relatedComedians.map(\.name) == ["Atsuko Okatsuka"])
        #expect(content.relatedContentMessage == nil)
    }

    @Test("comedian detail surfaces API failures explicitly")
    func comedianDetailShowsErrorState() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        await model.loadIfNeeded(
            apiClient: makeClient(
                comedianResponse: .status(.notFound),
                upcomingRunsResponse: .success(.init(data: [])),
                coBillResponse: .success(.init(data: []))
            ),
            favorites: ComedianFavoriteStore()
        )

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected failure phase, got \(model.phase)")
            return
        }
        #expect(failure.message == "This comedian could not be found. (HTTP 404)")
    }

    @Test("comedian detail renders explicit empty states for missing related content")
    func comedianDetailShowsEmptyStates() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        await model.loadIfNeeded(
            apiClient: makeClient(
                comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                upcomingRunsResponse: .success(.init(data: [])),
                coBillResponse: .success(.init(data: []))
            ),
            favorites: ComedianFavoriteStore()
        )

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }
        #expect(content.upcomingRuns.isEmpty)
        #expect(content.relatedComedians.isEmpty)
        #expect(content.relatedContentMessage == nil)
    }

    @Test("comedian detail keeps profile content visible when related shows fail")
    func comedianDetailShowsRelatedContentWarning() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        await model.loadIfNeeded(
            apiClient: makeClient(
                comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                upcomingRunsResponse: .status(.internalServerError),
                coBillResponse: .success(.init(data: []))
            ),
            favorites: ComedianFavoriteStore()
        )

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }
        #expect(content.comedian.name == "Mark Normand")
        #expect(content.upcomingRuns.isEmpty)
        #expect(content.relatedComedians.isEmpty)
        #expect(content.relatedContentMessage == "LaughTrack hit a server error while loading related shows.")
    }

    @Test("related comedians are ranked by shared bill frequency and capped")
    func relatedComediansAreRankedByFrequency() {
        let headliner = DemoContent.primaryComedian
        let firstSeenLowCount = makeLineup(name: "First Seen", uuid: "first-seen", id: 201)
        let firstSeenHighCount = makeLineup(name: "First High", uuid: "first-high", id: 202)
        let secondSeenHighCount = makeLineup(name: "Second High", uuid: "second-high", id: 203)
        let thirdSeenHighCount = makeLineup(name: "Third High", uuid: "third-high", id: 204)
        let fourthSeenHighCount = makeLineup(name: "Fourth High", uuid: "fourth-high", id: 205)
        let cappedOut = makeLineup(name: "Capped Out", uuid: "capped-out", id: 206)

        let shows = [
            showWithLineup(id: 401, lineup: [headliner.asLineup, firstSeenLowCount, firstSeenHighCount, secondSeenHighCount]),
            showWithLineup(id: 402, lineup: [headliner.asLineup, firstSeenHighCount, thirdSeenHighCount]),
            showWithLineup(id: 403, lineup: [headliner.asLineup, secondSeenHighCount, thirdSeenHighCount, fourthSeenHighCount]),
            showWithLineup(id: 404, lineup: [headliner.asLineup, fourthSeenHighCount, cappedOut]),
        ]

        let ranked = ComedianRelatedPresentation.rankedRelatedComedians(
            candidates: [cappedOut, firstSeenLowCount, fourthSeenHighCount, thirdSeenHighCount, secondSeenHighCount, firstSeenHighCount],
            shows: shows,
            currentComedianUUID: headliner.uuid
        )

        #expect(ranked.map(\.uuid) == [
            "first-high",
            "second-high",
            "third-high",
            "fourth-high",
            "first-seen",
        ])
    }

    @Test("comedian stats summarize upcoming shows by city and combined social followers")
    func comedianStatsAggregateUpcomingAndFollowers() {
        let comedian = DemoContent.primaryComedian
        let runs: [Components.Schemas.UpcomingRun] = [
            // Two NY clubs in the same city collapse to one city.
            fallbackRun(showIDs: [301, 302], clubID: 201, clubName: "Comedy Cellar", clubCity: "New York", clubState: "NY"),
            fallbackRun(showIDs: [303], clubID: 202, clubName: "The Stand", clubCity: "New York", clubState: "NY"),
            fallbackRun(showIDs: [304], clubID: 203, clubName: "Punch Line", clubCity: "San Francisco", clubState: "CA"),
        ]

        let stats = ComedianStatsPresentation.stats(for: comedian, runs: runs)
        let labels = stats.map(ComedianStatsPresentation.label(for:))

        #expect(labels.contains("4 upcoming shows in 2 cities"))
        // primaryComedian follower totals = 370k + 210k + 128k = 708,000 → "708K"
        #expect(labels.contains("708K social followers"))
    }

    @Test("comedian stats omit city count when no city is available")
    func comedianStatsOmitCityCountWhenMissing() {
        let comedian = DemoContent.primaryComedian
        let runs: [Components.Schemas.UpcomingRun] = [
            fallbackRun(showIDs: [301], clubID: 201, clubName: "Comedy Cellar"),
        ]

        let stats = ComedianStatsPresentation.stats(for: comedian, runs: runs)
        let labels = stats.map(ComedianStatsPresentation.label(for:))

        #expect(labels.contains("1 upcoming show"))
    }

    @Test("comedian stats omit zero-valued buckets")
    func comedianStatsOmitEmptyBuckets() {
        var comedian = DemoContent.primaryComedian
        comedian.socialData = .init(id: 0)

        let stats = ComedianStatsPresentation.stats(for: comedian, runs: [])

        #expect(stats.isEmpty)
    }

    @Test("podcast appearances expose playable episode metadata")
    func podcastAppearancesExposePlayableEpisodeMetadata() throws {
        let appearance = makePodcastAppearance(
            episodeTitle: "Comedy Cellar Stories",
            podcastTitle: "The Laugh Track Pod",
            audioURL: "https://cdn.example.com/episodes/cellar.mp3",
            episodeURL: "https://podcasts.example.com/cellar"
        )

        let item = try #require(ComedianPodcastPresentation.playbackItem(for: appearance))

        #expect(item.id == appearance.id)
        #expect(item.episodeTitle == "Comedy Cellar Stories")
        #expect(item.podcastName == "The Laugh Track Pod")
        #expect(item.audioURL?.absoluteString == "https://cdn.example.com/episodes/cellar.mp3")
        #expect(item.episodeURL?.absoluteString == "https://podcasts.example.com/cellar")
    }

    @Test("podcast appearances expose display role for row badges")
    func podcastAppearancesExposeDisplayRoleForRowBadges() throws {
        let host = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(role: "host")
        ))
        let cohost = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(role: "cohost")
        ))
        let guest = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(role: "guest")
        ))

        #expect(host.displayRole == "Host")
        #expect(cohost.displayRole == "Cohost")
        #expect(guest.displayRole == "Guest")
    }

    @Test("comedian detail includes a podcasts section tab")
    func comedianDetailIncludesPodcastsSectionTab() {
        #expect(ComedianDetailTab.allCases.map(\.title) == ["Upcoming", "Past", "Related", "Podcasts"])
    }

    @Test("podcast appearances fall back to external episodes when audio is unavailable")
    func podcastAppearancesFallbackToExternalEpisodeWhenAudioIsUnavailable() throws {
        let appearance = makePodcastAppearance(
            audioURL: "not a url",
            episodeURL: "https://podcasts.example.com/fallback"
        )

        let item = try #require(ComedianPodcastPresentation.playbackItem(for: appearance))

        #expect(item.audioURL == nil)
        #expect(item.episodeURL?.absoluteString == "https://podcasts.example.com/fallback")
        #expect(item.requiresExternalFallback == true)
    }

    @Test("podcast player keeps current episode across view navigation and supports controls")
    func podcastPlayerKeepsEpisodeAcrossNavigationAndSupportsControls() throws {
        let player = PodcastPlaybackController(audioEngine: RecordingPodcastAudioEngine())
        let firstItem = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(id: 501, episodeTitle: "First", audioURL: "https://cdn.example.com/first.mp3")
        ))
        let secondItem = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(id: 502, episodeTitle: "Second", audioURL: "https://cdn.example.com/second.mp3")
        ))

        player.start(firstItem)
        #expect(player.currentItem == firstItem)
        #expect(player.isPlaying == true)

        player.pause()
        #expect(player.currentItem == firstItem)
        #expect(player.isPlaying == false)

        player.resume()
        #expect(player.currentItem == firstItem)
        #expect(player.isPlaying == true)

        player.start(secondItem)
        #expect(player.currentItem == secondItem)
        #expect(player.isPlaying == true)

        player.dismiss()
        #expect(player.currentItem == nil)
        #expect(player.isPlaying == false)
    }

    @Test("podcast player records failed audio URLs and exposes the external fallback")
    func podcastPlayerRecordsFailedAudioURLsAndExposesExternalFallback() throws {
        let player = PodcastPlaybackController(audioEngine: RecordingPodcastAudioEngine())
        let item = try #require(ComedianPodcastPresentation.playbackItem(
            for: makePodcastAppearance(
                audioURL: "https://cdn.example.com/broken.mp3",
                episodeURL: "https://podcasts.example.com/broken"
            )
        ))

        player.start(item)
        player.markCurrentItemFailed()

        #expect(player.currentItem?.id == item.id)
        #expect(player.isPlaying == false)
        #expect(player.currentItem?.requiresExternalFallback == true)
    }

    @Test("loadPastShowsIfNeeded surfaces the first page on success")
    func loadPastShowsIfNeededReturnsFirstPage() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let pastShows = (1...3).map { fallbackShow(id: 500 + $0) }
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                .success(.init(data: pastShows, total: 25)),
            ]
        )

        await model.loadPastShowsIfNeeded(apiClient: client, comedianName: "Mark Normand")

        guard case .success(let page) = model.pastShowsPhase else {
            Issue.record("Expected past-shows success phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(page.shows.map(\.id) == [501, 502, 503])
        #expect(page.total == 25)
        #expect(page.page == 0)
        #expect(page.canLoadMore == true)
        #expect(model.pastShowsPaginationFailure == nil)
    }

    @Test("loadPastShowsIfNeeded reports an empty page when there are no past shows")
    func loadPastShowsIfNeededHandlesEmptyPage() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                .success(.init(data: [], total: 0)),
            ]
        )

        await model.loadPastShowsIfNeeded(apiClient: client, comedianName: "Mark Normand")

        guard case .success(let page) = model.pastShowsPhase else {
            Issue.record("Expected past-shows success phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(page.shows.isEmpty)
        #expect(page.total == 0)
        #expect(page.page == 0)
        #expect(page.canLoadMore == false)
    }

    @Test("loadPastShowsIfNeeded is a no-op after the first successful fetch")
    func loadPastShowsIfNeededIsIdempotent() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                // Single response. A second past-shows call would trip
                // Issue.record inside the mock, failing the test.
                .success(.init(data: [fallbackShow(id: 600)], total: 1)),
            ]
        )

        await model.loadPastShowsIfNeeded(apiClient: client, comedianName: "Mark Normand")
        await model.loadPastShowsIfNeeded(apiClient: client, comedianName: "Mark Normand")

        guard case .success(let page) = model.pastShowsPhase else {
            Issue.record("Expected past-shows success phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(page.shows.map(\.id) == [600])
    }

    @Test("loadMorePastShows appends the next page, advances page index, and flips canLoadMore at totals")
    func loadMorePastShowsAppendsAndAdvances() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let firstPage = (1...20).map { fallbackShow(id: 700 + $0) }
        let secondPage = (1...20).map { fallbackShow(id: 800 + $0) }
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                .success(.init(data: firstPage, total: 40)),
                .success(.init(data: secondPage, total: 40)),
            ]
        )

        await model.loadPastShowsIfNeeded(apiClient: client, comedianName: "Mark Normand")
        guard case .success(let initial) = model.pastShowsPhase else {
            Issue.record("Expected initial past-shows success phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(initial.shows.count == 20)
        #expect(initial.page == 0)
        #expect(initial.canLoadMore == true)

        await model.loadMorePastShows(apiClient: client, comedianName: "Mark Normand")

        guard case .success(let combined) = model.pastShowsPhase else {
            Issue.record("Expected combined past-shows success phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(combined.shows.count == 40)
        #expect(Array(combined.shows.prefix(20)).map(\.id) == firstPage.map(\.id))
        #expect(Array(combined.shows.suffix(20)).map(\.id) == secondPage.map(\.id))
        #expect(combined.page == 1)
        #expect(combined.canLoadMore == false)
        #expect(model.isLoadingMorePastShows == false)
        #expect(model.pastShowsPaginationFailure == nil)
    }

    @Test("loadMorePastShows is a no-op before the first page lands")
    func loadMorePastShowsRequiresInitialSuccess() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: []
        )

        await model.loadMorePastShows(apiClient: client, comedianName: "Mark Normand")

        // Phase stays idle (no API call) — the mock would Issue.record if it had been hit.
        guard case .idle = model.pastShowsPhase else {
            Issue.record("Expected past-shows phase to remain idle, got \(model.pastShowsPhase)")
            return
        }
    }

    @Test("reloadPastShows surfaces rate-limit retry-after messaging")
    func reloadPastShowsSurfacesRateLimit() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                .statusWithRetryAfter(.tooManyRequests, retryAfter: 5),
            ]
        )

        await model.reloadPastShows(apiClient: client, comedianName: "Mark Normand")

        guard case .failure(let failure) = model.pastShowsPhase else {
            Issue.record("Expected past-shows failure phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(failure.message == "LaughTrack is rate-limiting past shows right now. Please try again in 5 seconds. (HTTP 429)")
        guard case .rateLimited(let retryAfter, _) = failure else {
            Issue.record("Expected .rateLimited, got \(failure)")
            return
        }
        #expect(retryAfter == 5)
    }

    @Test("reloadPastShows surfaces server-error retry messaging")
    func reloadPastShowsSurfacesServerError() async throws {
        let model = ComedianDetailModel(comedianID: 101)
        let client = makeClient(
            comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
            upcomingRunsResponse: .success(.init(data: [])),
            coBillResponse: .success(.init(data: [])),
            pastShowsResponses: [
                .status(.internalServerError),
            ]
        )

        await model.reloadPastShows(apiClient: client, comedianName: "Mark Normand")

        guard case .failure(let failure) = model.pastShowsPhase else {
            Issue.record("Expected past-shows failure phase, got \(model.pastShowsPhase)")
            return
        }
        #expect(failure.message == "LaughTrack hit a server error. Please retry in a moment. (HTTP 500)")
        guard case .serverError(let status, _) = failure else {
            Issue.record("Expected .serverError, got \(failure)")
            return
        }
        #expect(status == 500)
    }

    private func makeClient(
        comedianResponse: MockComedianDetailTransport.EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>,
        upcomingRunsResponse: MockComedianDetailTransport.EntityResponse<Components.Schemas.UpcomingRunResponse>,
        coBillResponse: MockComedianDetailTransport.EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>,
        pastShowsResponses: [MockComedianDetailTransport.EntityResponse<Operations.GetComedianPastShows.Output.Ok.Body.JsonPayload>] = []
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockComedianDetailTransport(
                comedianResponse: comedianResponse,
                upcomingRunsResponse: upcomingRunsResponse,
                coBillResponse: coBillResponse,
                pastShowsResponses: pastShowsResponses
            )
        )
    }

    private func fallbackRelatedComedian() -> Components.Schemas.ComedianLineup {
        .init(
            name: "Atsuko Okatsuka",
            imageUrl: "https://example.com/atsuko.png",
            uuid: "demo-comedian-102",
            id: 102,
            userId: nil,
            socialData: .init(
                id: 2,
                instagramAccount: "atsukocomedy",
                instagramFollowers: 10,
                tiktokAccount: nil,
                tiktokFollowers: nil,
                youtubeAccount: nil,
                youtubeFollowers: nil,
                website: nil,
                popularity: nil,
                linktree: nil
            ),
            isFavorite: false,
            showCount: 5
        )
    }

    private func fallbackShow(
        id: Int,
        clubID: Int = 101,
        clubName: String = "Comedy Cellar",
        clubCity: String? = nil,
        clubState: String? = nil
    ) -> Components.Schemas.Show {
        .init(
            id: id,
            clubID: clubID,
            clubName: clubName,
            clubCity: clubCity,
            clubState: clubState,
            date: Date().addingTimeInterval(60 * 60 * 24),
            tickets: nil,
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: [
                .init(
                    name: "Mark Normand",
                    imageUrl: DemoContent.primaryComedian.imageUrl,
                    uuid: DemoContent.primaryComedian.uuid,
                    id: DemoContent.primaryComedian.id,
                    userId: nil,
                    socialData: DemoContent.primaryComedian.socialData,
                    isFavorite: false,
                    showCount: 12
                ),
                .init(
                    name: "Atsuko Okatsuka",
                    imageUrl: "https://example.com/atsuko.png",
                    uuid: "demo-comedian-102",
                    id: 102,
                    userId: nil,
                    socialData: .init(
                        id: 2,
                        instagramAccount: "atsukocomedy",
                        instagramFollowers: 10,
                        tiktokAccount: nil,
                        tiktokFollowers: nil,
                        youtubeAccount: nil,
                        youtubeFollowers: nil,
                        website: nil,
                        popularity: nil,
                        linktree: nil
                    ),
                    isFavorite: false,
                    showCount: 5
                )
            ],
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: nil,
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: 2.0
        )
    }

    private func makeLineup(name: String, uuid: String, id: Int) -> Components.Schemas.ComedianLineup {
        .init(
            name: name,
            imageUrl: "https://example.com/\(uuid).png",
            uuid: uuid,
            id: id,
            userId: nil,
            socialData: .init(
                id: id,
                instagramAccount: nil,
                instagramFollowers: nil,
                tiktokAccount: nil,
                tiktokFollowers: nil,
                youtubeAccount: nil,
                youtubeFollowers: nil,
                website: nil,
                popularity: nil,
                linktree: nil
            ),
            isFavorite: false,
            showCount: 1
        )
    }

    private func showWithLineup(id: Int, lineup: [Components.Schemas.ComedianLineup]) -> Components.Schemas.Show {
        var show = fallbackShow(id: id)
        show.lineup = lineup
        return show
    }

    private func fallbackRun(
        showIDs: [Int],
        clubID: Int = 101,
        clubName: String = "Comedy Cellar",
        clubCity: String? = nil,
        clubState: String? = nil
    ) -> Components.Schemas.UpcomingRun {
        .init(
            clubID: clubID,
            clubName: clubName,
            clubImageUrl: "https://example.com/show.png",
            shows: showIDs.map {
                fallbackShow(
                    id: $0,
                    clubID: clubID,
                    clubName: clubName,
                    clubCity: clubCity,
                    clubState: clubState
                )
            }
        )
    }

    private func makePodcastAppearance(
        id: Int = 401,
        role: String = "guest",
        episodeTitle: String = "Podcast Episode",
        podcastTitle: String = "Comedy Podcast",
        audioURL: String = "https://cdn.example.com/episode.mp3",
        episodeURL: String? = "https://podcasts.example.com/episode"
    ) -> Components.Schemas.PodcastAppearance {
        .init(
            id: id,
            role: role,
            podcast: .init(
                id: 301,
                source: "podchaser",
                sourcePodcastId: "podcast-\(id)",
                title: podcastTitle
            ),
            episode: .init(
                id: 701,
                source: "podchaser",
                sourceEpisodeId: "episode-\(id)",
                title: episodeTitle,
                audioUrl: audioURL,
                episodeUrl: episodeURL,
                hosts: [],
                guests: []
            )
        )
    }
}

private final class RecordingPodcastAudioEngine: PodcastAudioEngine {
    private(set) var loadedURL: URL?
    private(set) var playCount = 0
    private(set) var pauseCount = 0

    func load(url: URL, onFailure: @escaping @MainActor () -> Void) {
        loadedURL = url
    }

    func play() {
        playCount += 1
    }

    func pause() {
        pauseCount += 1
    }

    func stop() {
        loadedURL = nil
    }
}

private extension Components.Schemas.ComedianDetail {
    var asLineup: Components.Schemas.ComedianLineup {
        .init(
            name: name,
            imageUrl: imageUrl,
            uuid: uuid,
            id: id,
            userId: nil,
            socialData: socialData,
            isFavorite: false,
            showCount: nil
        )
    }
}

private struct MockComedianDetailTransport: ClientTransport {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
        case statusWithRetryAfter(HTTPResponse.Status, retryAfter: Int)
    }

    let comedianResponse: EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>
    let upcomingRunsResponse: EntityResponse<Components.Schemas.UpcomingRunResponse>
    let coBillResponse: EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>
    let pastShowsResponses: [EntityResponse<Operations.GetComedianPastShows.Output.Ok.Body.JsonPayload>]
    let pastShowsCallCount = PastShowsCallCount()

    init(
        comedianResponse: EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>,
        upcomingRunsResponse: EntityResponse<Components.Schemas.UpcomingRunResponse>,
        coBillResponse: EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>,
        pastShowsResponses: [EntityResponse<Operations.GetComedianPastShows.Output.Ok.Body.JsonPayload>] = []
    ) {
        self.comedianResponse = comedianResponse
        self.upcomingRunsResponse = upcomingRunsResponse
        self.coBillResponse = coBillResponse
        self.pastShowsResponses = pastShowsResponses
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "getComedian":
            return try encodedResponse(for: comedianResponse)
        case "getComedianUpcomingRuns":
            return try encodedResponse(for: upcomingRunsResponse)
        case "getComedianCoBill":
            return try encodedResponse(for: coBillResponse)
        case "getComedianPastShows":
            let index = pastShowsCallCount.next()
            guard index < pastShowsResponses.count else {
                Issue.record("Unexpected extra getComedianPastShows call at index \(index)")
                // Mirror the documented-status body shape so a decoder error
                // doesn't reroute the failure into the model's network catch.
                return (
                    HTTPResponse(
                        status: .internalServerError,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(#"{"error":"mock"}"#)
                )
            }
            return try encodedResponse(for: pastShowsResponses[index])
        default:
            Issue.record("Unexpected operation: \(operationID)")
            return (HTTPResponse(status: .internalServerError), nil)
        }
    }

    private func encodedResponse<Payload: Encodable>(
        for response: EntityResponse<Payload>
    ) throws -> (HTTPResponse, HTTPBody?) {
        switch response {
        case .success(let payload):
            let encoder = APIMockEncoder.make()
            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            // Error responses must conform to ErrorResponse schema (required `error`
            // field) — without it, the OpenAPI client throws and the model falls
            // through to its network catch instead of the documented status branch.
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(#"{"error":"mock"}"#)
            )
        case .statusWithRetryAfter(let status, let retryAfter):
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [
                        .contentType: "application/json",
                        .retryAfter: "\(retryAfter)",
                    ]
                ),
                HTTPBody(#"{"error":"mock"}"#)
            )
        }
    }
}

private final class PastShowsCallCount: @unchecked Sendable {
    private let lock = NSLock()
    private var value = 0
    func next() -> Int {
        lock.lock(); defer { lock.unlock() }
        let current = value
        value += 1
        return current
    }
}
