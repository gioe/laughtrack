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

@Suite("Podcast detail playback actions")
@MainActor
struct PodcastDetailPlaybackActionTests {
    @Test("resuming the same episode from an appearance preserves its position")
    func preservesPositionAcrossSurfaces() {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        player.start(Self.item(1, appearanceID: 101))
        player.seek(to: 123)
        player.pause()
        player.start(Self.item(1))
        #expect(engine.loadCount == 1)
        #expect(player.currentTime == 123)
        #expect(player.isPlaying)
    }

    static func item(_ episode: Int, appearanceID: Int? = nil, audio: Bool = true, external: Bool = true) -> PodcastPlaybackItem {
        PodcastPlaybackItem(id: appearanceID ?? episode, episodeID: episode, podcastID: 42,
            episodeTitle: "Episode \(episode)", podcastName: "Comedy conversations", podcastImageURL: nil,
            displayRole: "Guest", audioURL: audio ? URL(string: "https://example.com/\(episode).mp3") : nil,
            episodeURL: external ? URL(string: "https://example.com/episodes/\(episode)") : nil, failedAudioURL: nil)
    }
}

@MainActor
private final class DetailActionAudioEngine: PodcastAudioEngine {
    var loadCount = 0
    var playCount = 0
    var pauseCount = 0
    var failures: [() -> Void] = []
    var failSynchronously = false
    func load(url: URL, onFailure: @escaping () -> Void) {
        loadCount += 1
        failures.append(onFailure)
        if failSynchronously { onFailure() }
    }
    func play() { playCount += 1 }
    func pause() { pauseCount += 1 }
    func stop() {}
}

extension PodcastDetailPlaybackActionTests {
    @Test("actions track play pause resume and a different selected episode")
    func transportActions() {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let episode = Self.item(1)
        let appearance = Self.item(1, appearanceID: 901)
        #expect(player.detailAction(for: episode) == .play)
        #expect(player.performDetailAction(for: appearance) == nil)
        #expect(player.detailAction(for: episode) == .pause)
        #expect(player.detailAction(for: Self.item(2)) == .play)
        player.seek(to: 75)
        player.performDetailAction(for: episode)
        #expect(!player.isPlaying)
        #expect(engine.pauseCount == 1)
        #expect(player.detailAction(for: appearance) == .resume)
        player.performDetailAction(for: episode)
        #expect(player.isPlaying)
        #expect(player.currentTime == 75)
        #expect(engine.loadCount == 1)
        player.performDetailAction(for: Self.item(2))
        #expect(player.currentItem?.episodeID == 2)
        #expect(player.currentTime == 0)
        #expect(engine.loadCount == 2)
        #expect(player.detailAction(for: episode) == .play)
        #expect(player.detailAction(for: Self.item(2)) == .pause)
    }

    @Test("failure replaces stale fetched audio with an original episode action")
    func failureFallback() throws {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let episode = Self.item(1)
        player.performDetailAction(for: Self.item(1, appearanceID: 901))
        engine.failures[0]()
        let url = try #require(episode.episodeURL)
        #expect(!player.isPlaying)
        #expect(player.currentItem?.requiresExternalFallback == true)
        #expect(player.detailAction(for: episode) == .openOriginal(url))
        #expect(player.performDetailAction(for: episode) == url)
        #expect(engine.loadCount == 1)
        #expect(engine.playCount == 1)
    }

    @Test("unavailable audio preserves external links and cannot interrupt playback")
    func unavailableAudio() throws {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        player.start(Self.item(1))
        let external = Self.item(2, audio: false)
        #expect(player.detailAction(for: external) == .openOriginal(try #require(external.episodeURL)))
        #expect(player.performDetailAction(for: external) == external.episodeURL)
        #expect(player.detailAction(for: Self.item(3, audio: false, external: false)) == .unavailable)
        #expect(player.performDetailAction(for: Self.item(3, audio: false, external: false)) == nil)
        #expect(player.currentItem?.episodeID == 1)
        #expect(player.isPlaying)
        player.start(Self.item(4, external: false))
        engine.failures.last?()
        #expect(player.detailAction(for: Self.item(4, external: false)) == .unavailable)
    }

    @Test("failure from a previous load cannot fail a newly playing episode")
    func staleFailure() {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        player.start(Self.item(1))
        player.start(Self.item(2))
        engine.failures[0]()
        #expect(player.currentItem?.episodeID == 2)
        #expect(player.detailAction(for: Self.item(2)) == .pause)
        #expect(player.isPlaying)
        player.dismiss()
        player.start(Self.item(1))
        engine.failures[0]()
        #expect(player.detailAction(for: Self.item(1)) == .pause)
    }

    @Test("synchronous audio failure cannot publish a false playing state")
    func synchronousFailure() {
        let engine = DetailActionAudioEngine()
        engine.failSynchronously = true
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        player.start(Self.item(1))
        #expect(!player.isPlaying)
        #expect(engine.playCount == 0)
        #expect(player.currentItem?.requiresExternalFallback == true)
    }

    @Test("visible titles symbols and VoiceOver actions describe the next action")
    func accessibleActions() {
        for (action, title, symbol, label) in [
            (PodcastDetailPlaybackAction.play, "Play episode", "play.fill", "Play Episode 1"),
            (.pause, "Pause episode", "pause.fill", "Pause Episode 1"),
            (.resume, "Resume episode", "play.fill", "Resume Episode 1"),
        ] {
            #expect(action.title == title)
            #expect(action.symbolName == symbol)
            #expect(action.accessibilityLabel(episodeTitle: "Episode 1") == label)
        }
    }
}

#if canImport(UIKit)
import SwiftUI

@Suite("Podcast detail playback captures", .serialized)
@MainActor
struct PodcastDetailPlaybackCaptureTests {
    @Test("detail and catalog controls agree with the mini-player", arguments: ["playing", "paused", "failed"])
    func playbackSurfaces(_ state: String) async throws {
        let engine = DetailActionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let podcast = PodcastDetail(id: 42, title: "Comedy conversations", authorName: nil, websiteUrl: nil,
            feedUrl: nil, imageUrl: nil, description: "Stories from the stage, with a new comedian every week.", episodeCount: 2, hosts: [])
        let episode = PodcastDetailEpisode(id: 1, title: "Episode 1", description: "A conversation about writing jokes and life on the road.", releaseDate: "2026-09-20", durationSeconds: 1800,
            episodeUrl: "https://example.com/episodes/1", audioUrl: "https://example.com/1.mp3", appearances: [])
        let item = PodcastDetailPresentation.episodeItem(podcast: podcast, episode: episode)
        player.start(PodcastDetailPlaybackActionTests.item(1, appearanceID: 901))
        player.seek(to: 75)
        if state == "paused" { player.pause() }
        if state == "failed" { engine.failures[0]() }
        let expected: PodcastDetailPlaybackAction = state == "playing" ? .pause : state == "paused" ? .resume : .openOriginal(try #require(item.episodeURL))
        #expect(player.detailAction(for: item) == expected)
        let client = LaughTrackHostedViewTestSupport.makeClient()
        let auth = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "playback-actions")
        let catalogFetcher = PlaybackCatalogFetcher(response: .init(podcast: podcast, episodes: [episode], relatedComedians: []))
        for surface in ["episode", "catalog", "appearance"] {
            let screen: AnyView
            if surface == "episode" {
                screen = AnyView(PodcastEpisodeDetailView(episodeID: 1, apiClient: client,
                    fetcher: PlaybackEpisodeFetcher(response: .init(podcast: podcast, episode: episode))))
            } else if surface == "catalog" {
                screen = AnyView(PodcastDetailView(podcastID: 42, apiClient: client,
                    fetcher: catalogFetcher))
            } else {
                // Render the exact compact control used by comedian appearance rows.
                screen = AnyView(VStack(alignment: .leading, spacing: 24) {
                    Text("Comedian appearances").font(.title2)
                    HStack {
                        Text(item.episodeTitle)
                        Spacer()
                        PodcastDetailPlaybackButton(item: item, podcastPlayer: player, compact: true)
                    }
                    Text("Another episode")
                    PodcastDetailPlaybackButton(item: PodcastDetailPlaybackActionTests.item(2), podcastPlayer: player, compact: true)
                    Spacer()
                }.padding())
            }
            let host = HostedView(NavigationStack { screen }
                .safeAreaInset(edge: .bottom) { PodcastMiniPlayerView(player: player, apiClient: client).padding() }
                .environmentObject(TypedNavigationCoordinator<AppRoute>())
                .environmentObject(auth)
                .environmentObject(player)
                .environmentObject(PodcastFavoriteStore())
                .environmentObject(LoginModalPresenter())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "playback-actions"))
                .environment(\.scenePhase, .active)
                .environment(\.horizontalSizeClass, .compact), freshWindow: true, viewportSize: CGSize(width: 375, height: 812))
            await host.settle(iterations: 60)
            if surface == "catalog" { #expect(await catalogFetcher.loadCount > 0) }
            let image = try host.snapshot()
            #expect(image.size == CGSize(width: 375, height: 812))
            let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4026-\(surface)-\(state).png")
            try #require(image.pngData()).write(to: output)
            print("Playback action capture: \(output.path)")
        }
    }
}

private struct PlaybackEpisodeFetcher: PodcastEpisodeDetailFetching {
    let response: PodcastEpisodeDetailResponse
    func podcastEpisodeDetail(id: Int) async -> Result<PodcastEpisodeDetailResponse, LoadFailure> { .success(response) }
}
private actor PlaybackCatalogFetcher: PodcastDetailFetching {
    let response: PodcastDetailResponse
    private(set) var loadCount = 0
    init(response: PodcastDetailResponse) { self.response = response }
    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> {
        loadCount += 1
        return .success(response)
    }
}
#endif
