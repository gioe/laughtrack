import Foundation
import HTTPTypes
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
import OpenAPIRuntime
import Testing
@testable import LaughTrackApp

@Suite("Podcast episode detail view")
@MainActor
struct PodcastEpisodeDetailViewTests {
    @Test("episode detail route is Codable, non-shell, and coordinator-backed")
    func episodeDetailRouteIsTypedAndCodable() throws {
        let route = AppRoute.podcastEpisodeDetail(501)
        let encoded = try JSONEncoder().encode(route)
        let decoded = try JSONDecoder().decode(AppRoute.self, from: encoded)
        let coordinator = TypedNavigationCoordinator<AppRoute>()

        coordinator.push(route)

        #expect(decoded == route)
        #expect(route.shellTab == nil)
        #expect(decodedRoutes(in: coordinator, as: AppRoute.self) == [route])
    }

    @Test("model loads by episode id and retry replaces a failure with success")
    func modelLoadsAndRetries() async throws {
        let expected = Self.makeResponse()
        let fetcher = SequencePodcastEpisodeDetailFetcher(results: [
            .failure(.network("Offline")),
            .success(expected),
        ])
        let model = PodcastEpisodeDetailModel(episodeID: 501, fetcher: fetcher)

        await model.loadIfNeeded()
        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected initial failure, got \(model.phase)")
            return
        }
        #expect(failure == .network("Offline"))

        await model.reload()
        guard case .success(let response) = model.phase else {
            Issue.record("Expected retry success, got \(model.phase)")
            return
        }
        #expect(response == expected)
        #expect(await fetcher.requestedIDs() == [501, 501])
    }

    @Test("generated fetcher requests the episode path and maps the response")
    func generatedFetcherUsesEpisodeOperation() async throws {
        let schema = Self.makeSchemaResponse()
        let data = try JSONEncoder().encode(schema)
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(data)
            )
        }
        let client = Client(
            serverURL: URL(string: "https://example.test")!,
            transport: transport,
            middlewares: [APIVersionPathMiddleware()]
        )
        let fetcher = APIPodcastEpisodeDetailFetcher(apiClient: client)

        let result = await fetcher.podcastEpisodeDetail(id: 501)

        guard case .success(let response) = result else {
            Issue.record("Expected generated fetcher success, got \(result)")
            return
        }
        #expect(response.episode.id == 501)
        #expect(response.episode.description == "A full episode description.")
        #expect(response.podcast.id == 42)
        #expect(transport.capturedRequests.map(\.operationID) == ["getPodcastEpisode"])
        #expect(transport.capturedRequests.first?.path == "/api/v1/podcast-episodes/501")
    }

    @Test("generated fetcher classifies not found without exposing response copy")
    func generatedFetcherClassifiesNotFound() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            (
                HTTPResponse(status: .notFound, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"Internal record detail"}"#)
            )
        }
        let client = Client(
            serverURL: URL(string: "https://example.test")!,
            transport: transport,
            middlewares: [APIVersionPathMiddleware()]
        )
        let fetcher = APIPodcastEpisodeDetailFetcher(apiClient: client)

        let result = await fetcher.podcastEpisodeDetail(id: 999_999)

        #expect(result == .failure(.unexpected(
            status: 404,
            message: "This podcast episode could not be found."
        )))
    }

    @Test("generated schema maps podcast, full description, and accepted appearances")
    func generatedSchemaMapsDetailContent() {
        let mapped = PodcastEpisodeDetailResponse(schema: Self.makeSchemaResponse())

        #expect(mapped.podcast.title == "The Laugh Track Pod")
        #expect(mapped.podcast.hosts.map(\.name) == ["Mark Normand"])
        #expect(mapped.episode.title == "Comedy Cellar Stories")
        #expect(mapped.episode.description == "A full episode description.")
        #expect(mapped.episode.appearances.map(\.name) == [
            "Mark Normand",
            "Aparna Nancherla",
        ])
    }

    @Test("lineup keeps accepted podcast hosts and removes them from guests")
    func lineupPartitionsHostsAndGuests() {
        let lineup = PodcastEpisodeDetailPresentation.lineup(for: Self.makeResponse())

        #expect(lineup.hosts.map(\.id) == [101])
        #expect(lineup.hosts.map(\.name) == ["Mark Normand"])
        #expect(lineup.guests.map(\.id) == [202])
        #expect(lineup.guests.map(\.name) == ["Aparna Nancherla"])
    }

    @Test("audio-only episode resolves to direct playback")
    func audioOnlyEpisodeResolvesToPlayback() throws {
        let response = Self.makeResponse(audioURL: "https://cdn.example.com/cellar.mp3", episodeURL: nil)

        guard case .play(let item) = PodcastEpisodeDetailPresentation.primaryAction(for: response) else {
            Issue.record("Expected playable primary action")
            return
        }

        #expect(item.id == response.episode.id)
        #expect(item.episodeID == response.episode.id)
        #expect(item.audioURL?.absoluteString == "https://cdn.example.com/cellar.mp3")
        #expect(item.episodeURL == nil)
    }

    @Test("external-link-only episode opens its original page")
    func externalOnlyEpisodeResolvesToOriginalLink() throws {
        let response = Self.makeResponse(
            audioURL: "not a URL",
            episodeURL: "https://podcasts.example.com/cellar"
        )

        guard case .openOriginal(let url) = PodcastEpisodeDetailPresentation.primaryAction(for: response) else {
            Issue.record("Expected original-link primary action")
            return
        }

        #expect(url.absoluteString == "https://podcasts.example.com/cellar")
    }

    @Test("metadata-only episode stays present with unavailable playback")
    func metadataOnlyEpisodeResolvesToUnavailable() {
        let response = Self.makeResponse(audioURL: nil, episodeURL: nil)
        let rowItem = PodcastDetailPresentation.episodeItem(
            podcast: response.podcast,
            episode: response.episode
        )

        #expect(PodcastEpisodeDetailPresentation.primaryAction(for: response) == .unavailable)
        #expect(rowItem.episodeID == response.episode.id)
        #expect(rowItem.audioURL == nil)
        #expect(rowItem.episodeURL == nil)
        #expect(response.episode.title == "Comedy Cellar Stories")
        #expect(response.episode.description == "A full episode description.")
        #expect(PodcastEpisodeDetailPresentation.metadata(for: response.episode) == "Mar 1, 2026 • 1 hr 2 min")
    }

    @Test("date-only release metadata matches the screenshot fixture")
    func dateOnlyReleaseMetadataIncludesDateAndDuration() {
        let response = Self.makeResponse(
            releaseDate: "2026-08-01",
            durationSeconds: 8_940
        )

        #expect(
            PodcastEpisodeDetailPresentation.metadata(for: response.episode)
                == "Aug 1, 2026 • 2 hr 29 min"
        )
    }

    @Test("partial release metadata keeps whichever valid value is available")
    func partialReleaseMetadataStaysUseful() {
        let dateOnly = Self.makeResponse(
            releaseDate: "2026-08-01",
            durationSeconds: nil
        )
        let malformedDate = Self.makeResponse(
            releaseDate: "not-a-date",
            durationSeconds: 8_940
        )
        let missingDate = Self.makeResponse(
            releaseDate: nil,
            durationSeconds: 8_940
        )

        #expect(PodcastEpisodeDetailPresentation.metadata(for: dateOnly.episode) == "Aug 1, 2026")
        #expect(PodcastEpisodeDetailPresentation.metadata(for: malformedDate.episode) == "2 hr 29 min")
        #expect(PodcastEpisodeDetailPresentation.metadata(for: missingDate.episode) == "2 hr 29 min")
    }

    @Test("comedian episode rows preserve the episode id independently from appearance identity")
    func comedianEpisodeRowsPreserveEpisodeIdentity() throws {
        let appearance = Components.Schemas.PodcastAppearance(
            id: 401,
            role: "guest",
            podcast: .init(
                id: 42,
                source: "podchaser",
                sourcePodcastId: "podcast-42",
                title: "The Laugh Track Pod"
            ),
            episode: .init(
                id: 501,
                source: "podchaser",
                sourceEpisodeId: "episode-501",
                title: "Comedy Cellar Stories",
                audioUrl: "",
                hosts: [],
                guests: []
            )
        )

        let item = try #require(ComedianPodcastPresentation.playbackItem(for: appearance))

        #expect(item.id == 401)
        #expect(item.episodeID == 501)
        #expect(item.audioURL == nil)
        #expect(item.episodeURL == nil)
    }

    @Test("episode detail and row actions expose stable accessibility identifiers")
    func accessibilityIdentifiersAreStable() {
        #expect(
            LaughTrackViewTestID.podcastEpisodeDetailScreen
                == "laughtrack.podcast-episode-detail.screen"
        )
        #expect(
            LaughTrackViewTestID.podcastEpisodeDetailPrimaryAction
                == "laughtrack.podcast-episode-detail.primary-action"
        )
        #expect(
            LaughTrackViewTestID.podcastEpisodeDetailPodcastLink
                == "laughtrack.podcast-episode-detail.podcast-link"
        )
        #expect(
            LaughTrackViewTestID.podcastEpisodeDetailComedianLink(202)
                == "laughtrack.podcast-episode-detail.comedian-202"
        )
        #expect(
            LaughTrackViewTestID.podcastEpisodeRow(501)
                == "laughtrack.podcast-episode.row-501"
        )
        #expect(
            LaughTrackViewTestID.podcastEpisodePlayButton(501)
                == "laughtrack.podcast-episode.play-501"
        )
    }

    private static func makeResponse(
        audioURL: String? = "https://cdn.example.com/cellar.mp3",
        episodeURL: String? = "https://podcasts.example.com/cellar",
        releaseDate: String? = "2026-03-01T00:00:00.000Z",
        durationSeconds: Int? = 3_720
    ) -> PodcastEpisodeDetailResponse {
        PodcastEpisodeDetailResponse(
            podcast: PodcastDetail(
                id: 42,
                title: "The Laugh Track Pod",
                authorName: "Laugh Track Network",
                websiteUrl: "https://podcasts.example.com",
                feedUrl: "https://podcasts.example.com/feed.xml",
                imageUrl: "https://cdn.example.com/podcast.jpg",
                description: "Comedy conversations.",
                episodeCount: 75,
                hosts: [
                    PodcastDetailHost(
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Mark Normand",
                        imageUrl: "https://cdn.example.com/mark.jpg"
                    )
                ]
            ),
            episode: PodcastDetailEpisode(
                id: 501,
                title: "Comedy Cellar Stories",
                description: "A full episode description.",
                releaseDate: releaseDate,
                durationSeconds: durationSeconds,
                episodeUrl: episodeURL,
                audioUrl: audioURL,
                appearances: [
                    PodcastDetailEpisodeAppearance(
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Mark Normand",
                        imageUrl: "https://cdn.example.com/mark.jpg"
                    ),
                    PodcastDetailEpisodeAppearance(
                        id: 202,
                        uuid: "demo-comedian-202",
                        name: "Aparna Nancherla",
                        imageUrl: "https://cdn.example.com/aparna.jpg"
                    ),
                ]
            )
        )
    }

    private static func makeSchemaResponse() -> Components.Schemas.PodcastEpisodeDetailResponse {
        .init(
            podcast: .init(
                id: 42,
                slug: "the-laugh-track-pod",
                title: "The Laugh Track Pod",
                authorName: "Laugh Track Network",
                websiteUrl: "https://podcasts.example.com",
                feedUrl: "https://podcasts.example.com/feed.xml",
                imageUrl: "https://cdn.example.com/podcast.jpg",
                description: "Comedy conversations.",
                episodeCount: 75,
                hosts: [
                    .init(
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Mark Normand",
                        imageUrl: "https://cdn.example.com/mark.jpg"
                    )
                ]
            ),
            episode: .init(
                id: 501,
                title: "Comedy Cellar Stories",
                description: "A full episode description.",
                releaseDate: "2026-03-01T00:00:00.000Z",
                durationSeconds: 3_720,
                episodeUrl: "https://podcasts.example.com/cellar",
                audioUrl: "https://cdn.example.com/cellar.mp3",
                appearances: [
                    .init(
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Mark Normand",
                        imageUrl: "https://cdn.example.com/mark.jpg"
                    ),
                    .init(
                        id: 202,
                        uuid: "demo-comedian-202",
                        name: "Aparna Nancherla",
                        imageUrl: "https://cdn.example.com/aparna.jpg"
                    ),
                ]
            )
        )
    }
}

private actor SequencePodcastEpisodeDetailFetcher: PodcastEpisodeDetailFetching {
    private var results: [Result<PodcastEpisodeDetailResponse, LoadFailure>]
    private var ids: [Int] = []

    init(results: [Result<PodcastEpisodeDetailResponse, LoadFailure>]) {
        self.results = results
    }

    func podcastEpisodeDetail(id: Int) async -> Result<PodcastEpisodeDetailResponse, LoadFailure> {
        ids.append(id)
        guard !results.isEmpty else {
            return .failure(.unexpected(status: 0, message: "No stubbed result"))
        }
        return results.removeFirst()
    }

    func requestedIDs() -> [Int] {
        ids
    }
}
