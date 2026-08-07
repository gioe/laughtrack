import Foundation
import HTTPTypes
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
import OpenAPIRuntime
import Testing
@testable import LaughTrackApp

@Suite("Home podcast episode discovery")
@MainActor
struct HomePodcastEpisodeDiscoveryTests {
    @Test("episode presentation includes discovery context and explainable recommendation")
    func episodePresentationIncludesDiscoveryContext() {
        let now = Date(timeIntervalSince1970: 1_786_003_200)
        let episode = makeEpisode(
            releaseDate: now.addingTimeInterval(-2 * 86_400),
            durationSeconds: 2_520,
            reason: .followedComedian,
            role: .guest
        )
        let item = HomePodcastEpisodeDiscoveryPresentation.item(
            from: episode,
            now: now,
            calendar: utcCalendar
        )

        #expect(item.id == 701)
        #expect(item.title == "A Fresh Set")
        #expect(item.podcastName == "The Green Room")
        #expect(item.artworkURL == "https://cdn.example.com/green-room.jpg")
        #expect(item.releaseMetadata == "2d ago · 42 min")
        #expect(item.comedianName == "Avery Stone")
        #expect(item.comedianRole == "Guest")
        #expect(item.recommendationReason == "Because you follow Avery Stone")
    }

    @Test("recommendation reasons stay human readable")
    func recommendationReasonsStayHumanReadable() {
        let expected: [(Components.Schemas.HomeFeedPodcastEpisodeRecommendation.ReasonPayload, String)] = [
            (.followedComedian, "Because you follow Avery Stone"),
            (.favoritePodcast, "From a favorite podcast"),
            (.guestAppearance, "Guest appearance by Avery Stone"),
            (.popularComedian, "Featuring popular comedian Avery Stone"),
            (.recentEpisode, "A recent episode with Avery Stone"),
        ]

        for (reason, label) in expected {
            let item = HomePodcastEpisodeDiscoveryPresentation.item(
                from: makeEpisode(reason: reason),
                now: Date(timeIntervalSince1970: 1_786_003_200),
                calendar: utcCalendar
            )
            #expect(item.recommendationReason == label)
        }
    }

    @Test("detail selection and playback are separate actions")
    func detailSelectionAndPlaybackAreSeparateActions() throws {
        let item = HomePodcastEpisodeDiscoveryPresentation.item(from: makeEpisode())
        #expect(HomePodcastEpisodeDiscoveryPresentation.route(for: item) == .podcastEpisodeDetail(701))

        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let engine = RecordingPodcastAudioEngine()
        let player = PodcastPlaybackController(audioEngine: engine, registersRemoteCommands: false)
        let playbackItem = try #require(item.playbackItem)

        player.start(playbackItem)

        #expect(player.currentItem == playbackItem)
        #expect(player.isPlaying)
        #expect(engine.loadedURL == URL(string: "https://cdn.example.com/fresh-set.mp3"))
        #expect(engine.playCount == 1)
        #expect(decodedRoutes(in: coordinator, as: AppRoute.self).isEmpty)
    }

    @Test("unavailable audio omits the play action but keeps detail navigation")
    func unavailableAudioOmitsPlayAction() {
        let item = HomePodcastEpisodeDiscoveryPresentation.item(from: makeEpisode(audioURL: nil))

        #expect(item.playbackItem == nil)
        #expect(HomePodcastEpisodeDiscoveryPresentation.route(for: item) == .podcastEpisodeDetail(701))
    }

    @Test("missing and empty episode recommendations use legacy podcasts")
    func missingAndEmptyRecommendationsUseLegacyPodcasts() {
        let legacy = makeLegacyPodcast()

        #expect(HomeTrendingPodcastsModel.content(from: makeFeed(
            podcastEpisodes: nil,
            trendingPodcasts: [legacy]
        )) == .legacyPodcasts([legacy]))
        #expect(HomeTrendingPodcastsModel.content(from: makeFeed(
            podcastEpisodes: [],
            trendingPodcasts: [legacy]
        )) == .legacyPodcasts([legacy]))
        #expect(HomeTrendingPodcastsModel.content(from: makeFeed(
            podcastEpisodes: [makeEpisode()],
            trendingPodcasts: [legacy]
        )) == .episodes([makeEpisode()]))
    }

    @Test("public cache fallback does not suppress a session-scoped episode fetch")
    func publicCacheFallbackDoesNotSuppressEpisodeFetch() async throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let cache = DataCache<LaughTrackCacheKey>()
        let persistentCache = PersistentMainPageCache(directory: directory)
        let key = LaughTrackCacheKey.homeFeed(zipCode: "10012", distanceMiles: 25)
        await MainPageCache.set(
            makeFeed(podcastEpisodes: nil, trendingPodcasts: [makeLegacyPodcast()]),
            forKey: key,
            in: cache,
            persistentCache: persistentCache
        )

        let response = Components.Schemas.HomeFeedResponse(
            data: makeFeed(podcastEpisodes: [makeEpisode()], trendingPodcasts: [makeLegacyPodcast()])
        )
        let payload = try APIMockEncoder.make().encode(response)
        let transport = StubClientTransport { _, _, _, _ in
            (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(payload)
            )
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
        let model = HomeTrendingPodcastsModel()

        await model.refresh(
            apiClient: client,
            zipCode: "10012",
            distanceMiles: 25,
            sessionDiscriminator: "account-a|session-1",
            cache: cache,
            persistentCache: persistentCache,
            coalescer: HomeFeedRequestCoalescer()
        )

        #expect(transport.capturedRequests.count == 1)
        guard case .success(.episodes(let episodes)) = model.phase else {
            Issue.record("Expected network episode recommendations after the public fallback")
            return
        }
        #expect(episodes.map(\.id) == [701])
        let publicValue: Components.Schemas.HomeFeed? = await cache.get(forKey: key)
        #expect(publicValue?.podcastEpisodes == nil)
    }

    @Test("rail exposes Browse podcasts and distinct detail and play controls")
    func railExposesBrowseAndDistinctControls() throws {
        let source = try railSource()

        #expect(source.contains("actionTitle: \"Browse podcasts\""))
        #expect(source.contains("coordinator.push(HomePodcastEpisodeDiscoveryPresentation.route(for: item))"))
        #expect(source.contains("podcastPlayer.start(playbackItem)"))
        #expect(source.contains("homePodcastEpisodeButton(item.id)"))
        #expect(source.contains("homePodcastEpisodePlayButton(item.id)"))
    }

    private var utcCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func makeEpisode(
        releaseDate: Date = Date(timeIntervalSince1970: 1_786_003_200),
        durationSeconds: Int? = 2_520,
        audioURL: String? = "https://cdn.example.com/fresh-set.mp3",
        reason: Components.Schemas.HomeFeedPodcastEpisodeRecommendation.ReasonPayload = .guestAppearance,
        role: Components.Schemas.HomeFeedPodcastEpisodeRecommendation.AppearanceRolePayload = .guest
    ) -> Components.Schemas.HomeFeedPodcastEpisode {
        .init(
            id: 701,
            title: "A Fresh Set",
            description: "A new conversation about stand-up.",
            releaseDate: releaseDate,
            durationSeconds: durationSeconds,
            episodeUrl: "https://example.com/episodes/fresh-set",
            audioUrl: audioURL,
            podcast: .init(
                id: 91,
                slug: "the-green-room",
                title: "The Green Room",
                imageUrl: "https://cdn.example.com/green-room.jpg"
            ),
            recommendation: .init(
                reason: reason,
                comedian: .init(
                    id: 81,
                    uuid: "avery-stone",
                    name: "Avery Stone",
                    imageUrl: "https://cdn.example.com/avery.jpg"
                ),
                appearanceRole: role,
                followedComedian: reason == .followedComedian,
                favoritePodcast: reason == .favoritePodcast
            )
        )
    }

    private func makeLegacyPodcast() -> Components.Schemas.HomeFeedPodcast {
        .init(
            id: 91,
            slug: "the-green-room",
            title: "The Green Room",
            imageUrl: "https://cdn.example.com/green-room.jpg",
            episodeCount: 42
        )
    }

    private func makeFeed(
        podcastEpisodes: [Components.Schemas.HomeFeedPodcastEpisode]?,
        trendingPodcasts: [Components.Schemas.HomeFeedPodcast]
    ) -> Components.Schemas.HomeFeed {
        .init(
            hero: .init(zipCode: "10012", city: "New York", state: "NY", shows: []),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [],
            moreNearYou: [],
            trendingThisWeek: [],
            followedComedianShows: [],
            podcastEpisodes: podcastEpisodes,
            trendingPodcasts: trendingPodcasts,
            popularClubs: []
        )
    }

    private func railSource(filePath: String = #filePath) throws -> String {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent(
            "Sources/LaughTrackApp/Home/Views/Rails/HomeTrendingPodcastsRail.swift"
        )
        return try String(contentsOf: sourceURL, encoding: .utf8)
    }
}

@MainActor
private final class RecordingPodcastAudioEngine: PodcastAudioEngine {
    private(set) var loadedURL: URL?
    private(set) var playCount = 0

    func load(url: URL, onFailure: @escaping () -> Void) {
        loadedURL = url
    }

    func play() {
        playCount += 1
    }

    func pause() {}
    func stop() {}
}
