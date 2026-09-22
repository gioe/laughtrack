import Foundation
import HTTPTypes
import LaughTrackAPIClient
import Testing
@testable import LaughTrackApp
import LaughTrackCore
import OpenAPIRuntime

@Suite("Podcast detail view")
@MainActor
struct PodcastDetailViewTests {
    @Test("podcast detail model loads podcast, episodes, and related comedians")
    func podcastDetailModelLoadsContent() async throws {
        let response = PodcastDetailViewTests.makeResponse()
        let model = PodcastDetailModel(
            podcastID: 42,
            fetcher: RecordingPodcastDetailFetcher(result: .success(response))
        )

        await model.loadIfNeeded()

        guard case .success(let content) = model.phase else {
            Issue.record("Expected podcast detail success phase, got \(model.phase)")
            return
        }

        #expect(content.podcast.title == "The Laugh Track Pod")
        #expect(content.episodes.map(\.title) == ["Comedy Cellar Stories"])
        #expect(content.episodes[0].appearances.map(\.name) == ["Mark Normand"])
        #expect(content.relatedComedians.map(\.name) == ["Mark Normand"])
    }

    @Test("podcast detail model surfaces not found failures")
    func podcastDetailModelSurfacesFailures() async throws {
        let model = PodcastDetailModel(
            podcastID: 42,
            fetcher: RecordingPodcastDetailFetcher(
                result: .failure(.unexpected(status: 404, message: "This podcast could not be found."))
            )
        )

        await model.loadIfNeeded()

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected podcast detail failure phase, got \(model.phase)")
            return
        }

        #expect(failure.message == "This podcast could not be found. (HTTP 404)")
    }

    @Test("podcast detail generated-client fetcher uses shared failure classification")
    func podcastDetailGeneratedFetcherUsesSharedFailureClassification() async throws {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            (
                HTTPResponse(status: .badRequest, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"Custom bad-request copy"}"#)
            )
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.test")!,
            transport: transport,
            middlewares: [APIVersionPathMiddleware()]
        )
        let fetcher = APIPodcastDetailFetcher(apiClient: apiClient)

        let result = await fetcher.podcastDetail(id: 42)

        guard case .failure(let failure) = result else {
            Issue.record("Expected podcast detail fetcher to classify bad-request failure")
            return
        }
        #expect(failure.message == "LaughTrack could not apply those podcast details filters. (HTTP 400)")
    }

    @Test("podcast detail presentation creates playable episode rows")
    func podcastDetailPresentationCreatesPlayableRows() throws {
        let response = PodcastDetailViewTests.makeResponse()
        let item = try #require(PodcastDetailPresentation.playbackItem(
            podcast: response.podcast,
            episode: response.episodes[0]
        ))

        #expect(item.id == 501)
        #expect(item.podcastID == 42)
        #expect(item.episodeTitle == "Comedy Cellar Stories")
        #expect(item.podcastName == "The Laugh Track Pod")
        #expect(item.audioURL?.absoluteString == "https://cdn.example.com/cellar.mp3")
        #expect(item.episodeURL?.absoluteString == "https://podcasts.example.com/cellar")
        #expect(
            PodcastDetailPresentation.episodeMetadata(for: response.episodes[0])
                == "Mar 1, 2026 • 1 hr 2 min"
        )
    }

    @Test("podcast detail episode lineup hides podcast hosts")
    func podcastDetailEpisodeLineupHidesPodcastHosts() {
        let response = PodcastDetailViewTests.makeResponseWithGuestAppearance()
        let lineup = PodcastDetailPresentation.episodeLineup(
            for: response.episodes[0],
            podcast: response.podcast
        )

        #expect(lineup.map(\.id) == [202])
        #expect(lineup.map(\.name) == ["Aparna Nancherla"])
    }

    @Test("podcast detail hero exposes website and RSS actions")
    func podcastDetailHeroActionsExposeExternalLinks() {
        let podcast = PodcastDetailViewTests.makeResponse().podcast
        let actions = PodcastDetailPresentation.heroActions(for: podcast)

        #expect(PodcastDetailPresentation.heroBadges(for: podcast).isEmpty)
        #expect(actions.map(\.title) == ["Website", "RSS"])
        #expect(actions.compactMap(\.url).map(\.absoluteString) == [
            "https://podcasts.example.com",
            "https://podcasts.example.com/feed.xml",
        ])
    }

    @Test("frequent guests keeps comedians with 2+ appearances, drops hosts, caps at 3")
    func podcastDetailFrequentGuestsFilters() {
        let response = PodcastDetailViewTests.makeResponseForFrequentGuests()
        let guests = PodcastDetailPresentation.frequentGuests(
            for: response,
            cap: 3
        )

        // Mark Normand (id 101) is the host → excluded even with 3 appearances.
        // One-shot Guest (id 305) has only 1 appearance → excluded.
        // Aparna (202), Sam (303), Joe (304) each have 2+ → all retained, capped at 3.
        #expect(guests.map(\.id) == [202, 303, 304])
        #expect(guests.map(\.name) == ["Aparna Nancherla", "Sam Morril", "Joe Comedian"])
    }

    @Test("frequent guests returns empty when no comedian has multiple appearances")
    func podcastDetailFrequentGuestsEmptyWhenNoRepeat() {
        let response = PodcastDetailViewTests.makeResponseWithGuestAppearance()
        let guests = PodcastDetailPresentation.frequentGuests(for: response)
        #expect(guests.isEmpty)
    }

    @Test("podcast detail hero exposes internal host comedians, ignoring RSS author")
    func podcastDetailHeroHostsExposeInternalComedians() {
        let podcast = PodcastDetailViewTests.makeResponse().podcast
        let hosts = PodcastDetailPresentation.heroHosts(for: podcast)

        #expect(hosts.map(\.id) == [101])
        #expect(hosts.map(\.name) == ["Mark Normand"])
        #expect(hosts.map(\.imageURL) == ["https://cdn.example.com/mark.jpg"])
    }

    @Test("podcast detail hero hosts are empty when no internal host is linked")
    func podcastDetailHeroHostsEmptyWhenNoInternalHost() {
        let podcast = PodcastDetail(
            id: 99,
            title: "Network-Owned Podcast",
            authorName: "Generic Network",
            websiteUrl: nil,
            feedUrl: nil,
            imageUrl: nil,
            description: nil,
            episodeCount: 3,
            hosts: []
        )

        #expect(PodcastDetailPresentation.heroHosts(for: podcast).isEmpty)
    }

    @Test("podcast detail hero hosts pass through empty image URLs from server")
    func podcastDetailHeroHostsPassThroughEmptyImageURL() {
        let podcast = PodcastDetail(
            id: 99,
            title: "Test Podcast",
            authorName: nil,
            websiteUrl: nil,
            feedUrl: nil,
            imageUrl: nil,
            description: nil,
            episodeCount: 1,
            hosts: [
                PodcastDetailHost(
                    id: 200,
                    uuid: "host-without-image",
                    name: "Image-less Host",
                    imageUrl: ""
                )
            ]
        )

        let hosts = PodcastDetailPresentation.heroHosts(for: podcast)

        #expect(hosts.map(\.id) == [200])
        #expect(hosts.map(\.imageURL) == [""])
    }

    private static func makeResponse() -> PodcastDetailResponse {
        PodcastDetailResponse(
            podcast: PodcastDetail(
                id: 42,
                title: "The Laugh Track Pod",
                authorName: "Laugh Track Network",
                websiteUrl: "https://podcasts.example.com",
                feedUrl: "https://podcasts.example.com/feed.xml",
                imageUrl: "https://cdn.example.com/podcast.jpg",
                description: "Comedy conversations.",
                episodeCount: 12,
                hosts: [
                    PodcastDetailHost(
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Mark Normand",
                        imageUrl: "https://cdn.example.com/mark.jpg"
                    )
                ]
            ),
            episodes: [
                PodcastDetailEpisode(
                    id: 501,
                    title: "Comedy Cellar Stories",
                    description: "A set recap.",
                    releaseDate: "2026-03-01T00:00:00.000Z",
                    durationSeconds: 3_720,
                    episodeUrl: "https://podcasts.example.com/cellar",
                    audioUrl: "https://cdn.example.com/cellar.mp3",
                    appearances: [
                        PodcastDetailEpisodeAppearance(
                            id: 101,
                            uuid: "demo-comedian-101",
                            name: "Mark Normand",
                            imageUrl: "https://cdn.example.com/mark.jpg"
                        )
                    ]
                )
            ],
            relatedComedians: [
                PodcastRelatedComedian(
                    id: 101,
                    uuid: "demo-comedian-101",
                    name: "Mark Normand",
                    imageUrl: "https://cdn.example.com/mark.jpg"
                )
            ]
        )
    }

    private static func makeResponseForFrequentGuests() -> PodcastDetailResponse {
        let base = makeResponse()
        func makeAppearance(_ id: Int, _ name: String) -> PodcastDetailEpisodeAppearance {
            PodcastDetailEpisodeAppearance(
                id: id,
                uuid: "demo-comedian-\(id)",
                name: name,
                imageUrl: "https://cdn.example.com/\(id).jpg"
            )
        }
        let host = makeAppearance(101, "Mark Normand")
        let aparna = makeAppearance(202, "Aparna Nancherla")
        let sam = makeAppearance(303, "Sam Morril")
        let joe = makeAppearance(304, "Joe Comedian")
        let oneShot = makeAppearance(305, "One-shot Guest")

        func episode(_ id: Int, _ appearances: [PodcastDetailEpisodeAppearance]) -> PodcastDetailEpisode {
            PodcastDetailEpisode(
                id: id,
                title: "Ep \(id)",
                description: nil,
                releaseDate: nil,
                durationSeconds: 0,
                episodeUrl: nil,
                audioUrl: nil,
                appearances: appearances
            )
        }

        return PodcastDetailResponse(
            podcast: base.podcast,
            episodes: [
                episode(1, [host, aparna, sam]),
                episode(2, [host, aparna, joe]),
                episode(3, [host, sam, joe]),
                episode(4, [host, oneShot])
            ],
            relatedComedians: base.relatedComedians
        )
    }

    private static func makeResponseWithGuestAppearance() -> PodcastDetailResponse {
        let base = makeResponse()
        return PodcastDetailResponse(
            podcast: base.podcast,
            episodes: [
                PodcastDetailEpisode(
                    id: 502,
                    title: "Host and Guest",
                    description: nil,
                    releaseDate: "2026-03-02T00:00:00.000Z",
                    durationSeconds: 3_000,
                    episodeUrl: "https://podcasts.example.com/guest",
                    audioUrl: "https://cdn.example.com/guest.mp3",
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
                        )
                    ]
                )
            ],
            relatedComedians: base.relatedComedians
        )
    }
}

private struct RecordingPodcastDetailFetcher: PodcastDetailFetching {
    let result: Result<PodcastDetailResponse, LoadFailure>

    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> {
        result
    }
}

@Suite("Podcast introduction")
@MainActor
struct PodcastIntroductionTests {
    @Test("empty and markup-only descriptions do not create an introduction", arguments: [nil, "", "  \n ", "<p>&nbsp;</p>", "<script>ignore()</script>"] as [String?])
    func emptyDescriptions(_ description: String?) {
        #expect(PodcastDetailPresentation.introduction(for: PodcastIntroFixtures.podcast(description)) == nil)
    }

    @Test("introduction decodes source HTML while preserving paragraphs")
    func formattedDescription() {
        let podcast = PodcastIntroFixtures.podcast("<p>Comedy &amp; conversation.</p><p>Meet &#233;very guest.<br>Weekly.</p>")
        #expect(PodcastDetailPresentation.introduction(for: podcast) == "Comedy & conversation.\n\nMeet évery guest.\nWeekly.")
    }

    @Test("short introductions stay concise and long introductions can expand")
    func disclosurePolicy() throws {
        let short = try #require(PodcastDetailPresentation.introduction(for: PodcastIntroFixtures.podcast("Comedy every week.")))
        let long = try #require(PodcastDetailPresentation.introduction(for: PodcastIntroFixtures.podcast(PodcastIntroFixtures.longDescription)))
        #expect(!DetailTextCard.shouldCollapse(text: short, lineLimit: 3))
        #expect(DetailTextCard.shouldCollapse(text: long, lineLimit: 3))
        #expect(long.contains("Final paragraph"))
    }

    @Test("latest playable episode is selected by date rather than catalog order")
    func newestAudio() {
        let episodes = [PodcastIntroFixtures.episode(3, date: "2026-03-03", audio: nil), PodcastIntroFixtures.episode(1, date: "2026-03-01"), PodcastIntroFixtures.episode(2, date: "2026-03-02T12:00:00.000Z")]
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: episodes)?.id == 2)
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: Array(episodes.reversed()))?.id == 2)
    }

    @Test("valid release dates rank above missing and malformed dates")
    func missingDates() {
        let episodes = [PodcastIntroFixtures.episode(9, date: nil), PodcastIntroFixtures.episode(8, date: "not-a-date"), PodcastIntroFixtures.episode(1, date: "2020-01-01")]
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: episodes)?.id == 1)
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: Array(episodes.prefix(2)))?.id == 9)
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: Array(episodes.prefix(2).reversed()))?.id == 9)
    }

    @Test("equal dates use a deterministic episode ID tiebreaker")
    func equalDates() {
        let episodes = [PodcastIntroFixtures.episode(1, date: "2026-03-01"), PodcastIntroFixtures.episode(2, date: "2026-03-01T00:00:00Z")]
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: episodes)?.id == 2)
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: Array(episodes.reversed()))?.id == 2)
    }

    @Test("catalogs without audio offer browsing but no latest-play action")
    func noAudio() {
        let episodes = [nil, "", "  ", "javascript:alert(1)"].enumerated().map { index, audio in PodcastIntroFixtures.episode(index, date: "2026-03-01", audio: audio) }
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: episodes) == nil)
        #expect(PodcastDetailPresentation.latestPlayableEpisode(in: []) == nil)
        let external = PodcastDetailPresentation.episodeItem(podcast: PodcastIntroFixtures.podcast(nil), episode: episodes[0])
        #expect(external.episodeURL != nil)
        #expect(external.audioURL == nil)
    }
}

@MainActor
private enum PodcastIntroFixtures {
    static let longDescription = "<p>Comedians explore the stories behind their favorite jokes and welcome a new guest every week. Hear about life on the road, writing new material, and the moments that make a room laugh.</p><p>Each conversation brings a different perspective on stand-up and the people who create it.</p><p>Final paragraph: new episodes arrive every Monday.</p>"
    static func podcast(_ description: String?) -> PodcastDetail {
        PodcastDetail(id: 42, title: "The Laugh Track Pod", authorName: "Taylor", websiteUrl: "https://example.com", feedUrl: nil, imageUrl: nil, description: description, episodeCount: 2, hosts: [.init(id: 7, uuid: "host-7", name: "Taylor", imageUrl: "")])
    }
    static func episode(_ id: Int, date: String?, audio: String? = "https://example.com/audio.mp3") -> PodcastDetailEpisode {
        PodcastDetailEpisode(id: id, title: "Episode \(id): Comedy conversations", description: nil, releaseDate: date, durationSeconds: 1800, episodeUrl: "https://example.com/episode/\(id)", audioUrl: audio, appearances: [])
    }
}

#if canImport(UIKit)
import SwiftUI
import LaughTrackBridge

@Suite("Podcast introduction hosted", .serialized)
@MainActor
struct PodcastIntroductionHostedTests {
    @Test("latest-episode button starts the selected audio through the existing player")
    func startsLatestEpisode() {
        let engine = IntroductionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let action = PodcastLatestEpisodeAction(
            podcast: PodcastIntroFixtures.podcast(nil),
            episodes: [PodcastIntroFixtures.episode(1, date: "2026-03-01"), PodcastIntroFixtures.episode(2, date: "2026-03-02", audio: "https://example.com/new.mp3")],
            podcastPlayer: player
        )
        // Exercise the exact button action directly; hosted accessibility trees
        // are unavailable on some simulator runtimes.
        action.playLatestEpisode()
        #expect(player.currentItem?.episodeID == 2)
        #expect(engine.loadedURL?.absoluteString == "https://example.com/new.mp3")
        #expect(engine.playCount == 1)
        PodcastLatestEpisodeAction(podcast: PodcastIntroFixtures.podcast(nil), episodes: [], podcastPlayer: player).playLatestEpisode()
        #expect(player.currentItem?.episodeID == 2)
        #expect(engine.playCount == 1)
    }

    @Test("review introduction and catalog states", arguments: ["short", "long", "empty", "no-audio", "no-description"])
    func reviewStates(_ scenario: String) async throws {
        let description = scenario == "no-description" ? nil : scenario == "long" ? PodcastIntroFixtures.longDescription : "Comedians talk about the stories behind their favorite jokes. New conversations every week."
        let podcast = PodcastIntroFixtures.podcast(description)
        let episodes = scenario == "empty" ? [] : [PodcastIntroFixtures.episode(1, date: "2026-03-01", audio: scenario == "no-audio" ? nil : "https://example.com/old.mp3"), PodcastIntroFixtures.episode(2, date: "2026-03-02", audio: scenario == "no-audio" ? nil : "https://example.com/new.mp3")]
        let response = PodcastDetailResponse(podcast: podcast, episodes: episodes, relatedComedians: [])
        let auth = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "podcast-intro")
        let engine = IntroductionAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let host = HostedView(NavigationStack {
            PodcastDetailView(podcastID: 42, apiClient: LaughTrackHostedViewTestSupport.makeClient(), fetcher: IntroductionFetcher(response: response))
        }
        .environmentObject(TypedNavigationCoordinator<AppRoute>())
        .environmentObject(auth)
        .environmentObject(player)
        .environmentObject(PodcastFavoriteStore())
        .environmentObject(LoginModalPresenter())
        .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "podcast-intro"))
        .environment(\.scenePhase, .active)
        .environment(\.horizontalSizeClass, .compact), freshWindow: true, viewportSize: CGSize(width: 375, height: 812))
        await host.settle()
        let first = try host.snapshot()
        let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4025-\(scenario).png")
        try #require(first.pngData()).write(to: output)
        print("Podcast introduction capture: \(output.path)")
    }
}

private struct IntroductionFetcher: PodcastDetailFetching {
    let response: PodcastDetailResponse
    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> { .success(response) }
}
@MainActor
private final class IntroductionAudioEngine: PodcastAudioEngine {
    var loadedURL: URL?
    var playCount = 0
    func load(url: URL, onFailure: @escaping () -> Void) { loadedURL = url }
    func play() { playCount += 1 }
    func pause() {}
    func stop() {}
}
#endif

@Suite("Podcast frequent guest stability")
@MainActor
struct PodcastFrequentGuestStabilityTests {
    @Test("frequent guests rank by distinct episode count then ascending identity")
    func ranksFrequentGuests() {
        let response = Self.rankedResponse()
        #expect(PodcastDetailPresentation.frequentGuests(for: response).map(\.id) == [40, 10, 20])
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: 10).map(\.id) == [40, 10, 20, 30])
    }

    @Test("recomputing presentation preserves both membership and order")
    func repeatedPresentation() {
        let response = Self.rankedResponse()
        let expected = PodcastDetailPresentation.frequentGuests(for: response)
        for _ in 0..<30 {
            #expect(PodcastDetailPresentation.frequentGuests(for: response) == expected)
        }
    }

    @Test("response episode and appearance ordering cannot reorder the ranked guests")
    func inputOrderDoesNotMatter() {
        let response = Self.rankedResponse()
        let reordered = Self.response(episodes: response.episodes.reversed().map {
            Self.episode($0.id, Array($0.appearances.reversed()))
        })
        #expect(PodcastDetailPresentation.frequentGuests(for: reordered) == PodcastDetailPresentation.frequentGuests(for: response))
    }

    @Test("eligibility counts unique episodes and excludes both forms of host identity")
    func eligibilityAndHosts() {
        let oneEpisodeOnly = Self.guest(10)
        let eligible = Self.guest(20)
        let hostIDMatch = Self.guest(90, uuid: "different-uuid")
        let hostUUIDMatch = Self.guest(91, uuid: "host-90")
        let response = Self.response(episodes: [
            Self.episode(1, [oneEpisodeOnly, oneEpisodeOnly, eligible, hostIDMatch, hostUUIDMatch]),
            Self.episode(1, [oneEpisodeOnly, eligible]),
            Self.episode(2, [eligible, hostIDMatch, hostUUIDMatch])
        ])
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: 10).map(\.id) == [20])
    }

    @Test("caps never pad the guest list or admit ineligible guests")
    func caps() {
        let response = Self.rankedResponse()
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: 1).map(\.id) == [40])
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: 0).isEmpty)
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: -1).isEmpty)
        #expect(PodcastDetailPresentation.frequentGuests(for: response, cap: 100).count == 4)
        #expect(PodcastDetailPresentation.frequentGuests(for: Self.response(episodes: [])).isEmpty)
    }

    @Test("refresh preserves unchanged rankings and recomputes when episode counts change")
    func refreshPolicy() async {
        let initial = Self.rankedResponse()
        let promoted = Self.guest(30)
        let changed = Self.response(episodes: initial.episodes + [
            Self.episode(4, [promoted]), Self.episode(5, [promoted])
        ])
        let fetcher = FrequentGuestSequenceFetcher([initial, initial, changed])
        let model = PodcastDetailModel(podcastID: 42, fetcher: fetcher)
        await model.loadIfNeeded()
        guard case .success(let first) = model.phase else {
            Issue.record("Expected initial podcast details")
            return
        }
        let initialGuests = PodcastDetailPresentation.frequentGuests(for: first)
        await model.reload()
        guard case .success(let unchanged) = model.phase else {
            Issue.record("Expected unchanged refreshed podcast details")
            return
        }
        #expect(PodcastDetailPresentation.frequentGuests(for: unchanged) == initialGuests)
        await model.reload()
        guard case .success(let updated) = model.phase else {
            Issue.record("Expected updated podcast details")
            return
        }
        #expect(PodcastDetailPresentation.frequentGuests(for: updated).map(\.id) == [30, 40, 10])
        #expect(await fetcher.calls == 3)
    }

    @Test("opening another podcast derives its guests without retaining the previous selection")
    func otherPodcastPolicy() async {
        let first = Self.rankedResponse()
        let other = Self.response(podcastID: 99, episodes: [
            Self.episode(101, [Self.guest(70)]), Self.episode(102, [Self.guest(70)])
        ])
        let firstModel = PodcastDetailModel(podcastID: 42, fetcher: FrequentGuestSequenceFetcher([first]))
        let otherModel = PodcastDetailModel(podcastID: 99, fetcher: FrequentGuestSequenceFetcher([other]))
        await firstModel.loadIfNeeded()
        await otherModel.loadIfNeeded()
        guard case .success(let firstContent) = firstModel.phase,
              case .success(let otherContent) = otherModel.phase else {
            Issue.record("Expected both independently loaded podcasts")
            return
        }
        #expect(PodcastDetailPresentation.frequentGuests(for: firstContent).map(\.id) == [40, 10, 20])
        #expect(PodcastDetailPresentation.frequentGuests(for: otherContent).map(\.id) == [70])
    }

    private static func rankedResponse() -> PodcastDetailResponse {
        // Deliberately unsorted IDs and names: frequency wins, then identity,
        // independent of dictionary iteration or alphabetic display names.
        let guests = [guest(30, name: "Alpha"), guest(10, name: "Zulu"), guest(40, name: "Middle"), guest(20, name: "Beta")]
        return response(episodes: [episode(1, guests), episode(2, guests), episode(3, [guest(40, name: "Middle")])])
    }

    private static func guest(_ id: Int, name: String? = nil, uuid: String? = nil) -> PodcastDetailEpisodeAppearance {
        PodcastDetailEpisodeAppearance(id: id, uuid: uuid ?? "guest-\(id)", name: name ?? "Guest \(id)", imageUrl: nil)
    }

    private static func episode(_ id: Int, _ appearances: [PodcastDetailEpisodeAppearance]) -> PodcastDetailEpisode {
        PodcastDetailEpisode(id: id, title: "Episode \(id)", description: nil, releaseDate: nil,
            durationSeconds: nil, episodeUrl: nil, audioUrl: nil, appearances: appearances)
    }

    private static func response(podcastID: Int = 42, episodes: [PodcastDetailEpisode]) -> PodcastDetailResponse {
        PodcastDetailResponse(
            podcast: PodcastDetail(id: podcastID, title: "Podcast \(podcastID)", authorName: nil,
                websiteUrl: nil, feedUrl: nil, imageUrl: nil, description: nil,
                episodeCount: episodes.count,
                hosts: [PodcastDetailHost(id: 90, uuid: "host-90", name: "Host", imageUrl: "")]),
            episodes: episodes,
            relatedComedians: []
        )
    }
}

private actor FrequentGuestSequenceFetcher: PodcastDetailFetching {
    let responses: [PodcastDetailResponse]
    private(set) var calls = 0

    init(_ responses: [PodcastDetailResponse]) { self.responses = responses }

    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> {
        let response = responses[min(calls, responses.count - 1)]
        calls += 1
        return .success(response)
    }
}
