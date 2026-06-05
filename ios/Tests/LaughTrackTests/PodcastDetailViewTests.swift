import Foundation
import Testing
@testable import LaughTrackApp
import LaughTrackCore

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

        #expect(
            PodcastDetailPresentation.heroBadges(for: podcast).map(\.title)
                == ["12 episodes"]
        )
        #expect(actions.map(\.title) == ["Website", "RSS"])
        #expect(actions.compactMap(\.url).map(\.absoluteString) == [
            "https://podcasts.example.com",
            "https://podcasts.example.com/feed.xml",
        ])
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
