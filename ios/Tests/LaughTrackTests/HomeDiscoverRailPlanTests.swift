import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Home Discover rail plan")
@MainActor
struct HomeDiscoverRailPlanTests {
    @Test("home feed requests the iOS rail policy")
    func homeFeedRequestsIOSRailPolicy() async throws {
        let feed = makeFeed(
            railPlan: makePlan(rails: [])
        )
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "getHomeFeed")
            let data = try APIMockEncoder.make().encode(
                Components.Schemas.HomeFeedResponse(data: feed)
            )
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(data)
            )
        }
        let client = Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
        let model = HomeDiscoverRailPlanModel()

        await model.refresh(
            apiClient: client,
            zipCode: "10012",
            distanceMiles: 25,
            sessionDiscriminator: nil,
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        let request = try #require(transport.capturedRequests.first)
        #expect(queryValue("platform", from: request.path) == "ios")
        #expect(model.sections == [])
    }

    @Test("server order and item IDs define native rail contents")
    func serverOrderAndItemIDsDefineRailContents() throws {
        let feed = makeFeed(
            showsTonight: [makeShow(1), makeShow(2)],
            trendingThisWeek: [makeShow(3)],
            railPlan: makePlan(rails: [
                .init(
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 8,
                    itemIds: ["2", "1"]
                ),
                .init(
                    railKey: "trending_this_week",
                    payloadKey: "trendingThisWeek",
                    position: 2,
                    itemIds: ["3"]
                ),
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        #expect(sections.map(\.id) == ["trending_this_week", "shows_tonight"])
        #expect(sections.map(\.rank) == [2, 8])

        guard case .showsTonight(let shows) = sections[1].content else {
            Issue.record("Expected a native tonight rail")
            return
        }
        #expect(shows.map(\.id) == [2, 1])
    }

    @Test("best shows this week is limited to five shows")
    func bestShowsThisWeekIsLimitedToFiveShows() throws {
        let shows = (1...7).map(makeShow)
        let feed = makeFeed(
            trendingThisWeek: shows,
            railPlan: makePlan(rails: [
                .init(
                    railKey: "trending_this_week",
                    payloadKey: "trendingThisWeek",
                    position: 0,
                    itemIds: shows.map { String($0.id) }
                ),
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .trendingThisWeek(let limitedShows) = sections[0].content else {
            Issue.record("Expected a best-shows-this-week rail")
            return
        }

        #expect(limitedShows.map(\.id) == [1, 2, 3, 4, 5])
    }

    @Test("missing or incompatible plans preserve the legacy experience")
    func missingOrIncompatiblePlansPreserveLegacyExperience() {
        #expect(HomeDiscoverRailPlanPresentation.sections(from: makeFeed()) == nil)
        #expect(HomeDiscoverRailPlanPresentation.sections(from: makeFeed(
            railPlan: makePlan(version: 2, rails: [])
        )) == nil)
        #expect(HomeDiscoverRailPlanPresentation.sections(from: makeFeed(
            railPlan: makePlan(platform: .android, rails: [])
        )) == nil)
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .followedComedianShows,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
    }

    @Test("unknown and empty rails are skipped without changing stable IDs")
    func unknownAndEmptyRailsAreSkippedWithoutChangingStableIDs() throws {
        let dynamicItem = makeDynamicItem(id: 9, reason: "Ada is visiting New York")
        let dynamicRail = Components.Schemas.HomeFeedDynamicRail(
            railKey: "just_passing_through",
            label: "Just passing through",
            items: [dynamicItem]
        )
        let feed = makeFeed(
            dynamicRails: [dynamicRail],
            railPlan: makePlan(rails: [
                .init(
                    railKey: "future_server_rail",
                    payloadKey: "futurePayload",
                    position: 0,
                    itemIds: ["9"]
                ),
                .init(
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 1,
                    itemIds: ["404"]
                ),
                .init(
                    railKey: "just_passing_through",
                    payloadKey: "dynamicRails",
                    position: 7,
                    itemIds: ["9"]
                ),
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        #expect(sections.map(\.id) == ["just_passing_through"])
        #expect(sections[0].id == HomeDiscoverRailPlanPresentation.section(
            railKey: "just_passing_through",
            payloadKey: "dynamicRails",
            position: 99,
            itemIDs: ["9"],
            policyVersion: 3,
            feed: feed
        )?.id)

        guard case .dynamicShows(_, let items) = sections[0].content else {
            Issue.record("Expected a dynamic show rail")
            return
        }
        #expect(items[0].reason.label == "Ada is visiting New York")
    }

    @Test("podcast plans reuse structured episode discovery data")
    func podcastPlansReuseStructuredEpisodeDiscoveryData() throws {
        let episode = makeEpisode(id: 701)
        let feed = makeFeed(
            podcastEpisodes: [episode],
            railPlan: makePlan(rails: [
                .init(
                    railKey: "trending_podcasts",
                    payloadKey: "podcastEpisodes",
                    position: 0,
                    itemIds: ["701"]
                )
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .podcastEpisodes(let episodes) = sections[0].content else {
            Issue.record("Expected podcast episode presentation")
            return
        }
        #expect(episodes == [episode])
        #expect(HomePodcastEpisodeDiscoveryPresentation.item(from: episodes[0]).id == 701)
    }

    @Test("Episodes for you and Just passing through are limited to five items")
    func requestedRailsAreLimitedToFiveItems() throws {
        let episodes = (1...7).map(makeEpisode)
        let dynamicItems = (11...17).map {
            makeDynamicItem(id: $0, reason: "Comic \($0) is visiting")
        }
        let feed = makeFeed(
            podcastEpisodes: episodes,
            dynamicRails: [
                .init(
                    railKey: "just_passing_through",
                    label: "Just passing through",
                    items: dynamicItems
                )
            ],
            railPlan: makePlan(rails: [
                .init(
                    railKey: "trending_podcasts",
                    payloadKey: "podcastEpisodes",
                    position: 0,
                    itemIds: episodes.map { String($0.id) }
                ),
                .init(
                    railKey: "just_passing_through",
                    payloadKey: "dynamicRails",
                    position: 1,
                    itemIds: dynamicItems.map { String($0.id) }
                ),
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .podcastEpisodes(let limitedEpisodes) = sections[0].content,
              case .dynamicShows(_, let limitedShows) = sections[1].content else {
            Issue.record("Expected podcast and Just passing through rails")
            return
        }

        #expect(limitedEpisodes.map(\.id) == [1, 2, 3, 4, 5])
        #expect(limitedShows.map(\.id) == [11, 12, 13, 14, 15])
    }

    @Test("removed stacked lineups rail is ignored")
    func removedStackedLineupsRailIsIgnored() {
        let item = makeDynamicItem(id: 9, reason: "Three comedians")
        let feed = makeFeed(
            dynamicRails: [
                .init(
                    railKey: "stacked_lineups",
                    label: "Stacked lineups",
                    items: [item]
                )
            ],
            railPlan: makePlan(rails: [
                .init(
                    railKey: "stacked_lineups",
                    payloadKey: "dynamicRails",
                    position: 0,
                    itemIds: ["9"]
                )
            ])
        )

        #expect(HomeDiscoverRailPlanPresentation.sections(from: feed) == [])
    }

    @Test("just passing through features its associated comedian")
    func justPassingThroughFeaturesAssociatedComedian() {
        let item = makeDynamicItem(
            id: 9,
            reason: "Avery is visiting",
            performer: .init(id: 81, uuid: "avery-stone", name: "Avery Stone")
        )

        #expect(
            HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                railKey: "just_passing_through",
                item: item
            ) == 81
        )
        #expect(
            HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                railKey: "rare_returns",
                item: item
            ) == nil
        )
    }

    @Test("location changes refresh plans and planned show rails preserve See all handoff")
    func locationChangesRefreshPlansAndShowRailsPreserveSeeAllHandoff() throws {
        let testFileURL = URL(fileURLWithPath: #filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let homeView = try String(
            contentsOf: iosRoot.appendingPathComponent("Sources/LaughTrackApp/Home/Views/HomeView.swift"),
            encoding: .utf8
        )
        let plannedRail = try String(
            contentsOf: iosRoot.appendingPathComponent("Sources/LaughTrackApp/Home/Views/Rails/HomeDiscoverPlannedRail.swift"),
            encoding: .utf8
        )

        #expect(homeView.contains("@ObservedObject private var nearbyPreferenceStore"))
        #expect(homeView.contains(".task(id: railPlanRequestKey)"))
        #expect(plannedRail.contains("action: { openSeeAll(railKind: .showsTonight) }"))
        #expect(plannedRail.contains("seeMoreRailKind: .thisWeek"))
        #expect(plannedRail.contains("HomeShowsTonightModel.seeMoreSearchSeed("))
        #expect(plannedRail.contains("if section.id == \"just_passing_through\""))
        #expect(plannedRail.contains("HomeFeaturedShowsCarousel("))
        #expect(plannedRail.contains("preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredHeadlinerID("))
        #expect(plannedRail.contains("timestampLabel: ShowFormatting.featuredDateTime("))
    }
}

private func makePlan(
    version: Int = 1,
    platform: Components.Schemas.HomeFeedRailPlan.PlatformPayload = .ios,
    rails: [Components.Schemas.HomeFeedRailPlanEntry]
) -> Components.Schemas.HomeFeedRailPlan {
    .init(
        version: version,
        catalogVersion: 2,
        policyVersion: 3,
        platform: platform,
        cycleIndex: 0,
        rails: rails
    )
}

private func makeFeed(
    showsTonight: [Components.Schemas.Show] = [],
    trendingThisWeek: [Components.Schemas.Show] = [],
    podcastEpisodes: [Components.Schemas.HomeFeedPodcastEpisode]? = nil,
    dynamicRails: [Components.Schemas.HomeFeedDynamicRail]? = nil,
    railPlan: Components.Schemas.HomeFeedRailPlan? = nil
) -> Components.Schemas.HomeFeed {
    .init(
        hero: .init(zipCode: "10012", city: "New York", state: "NY", shows: []),
        trendingComedians: [],
        comediansNearYou: [],
        showsTonight: showsTonight,
        moreNearYou: [],
        trendingThisWeek: trendingThisWeek,
        followedComedianShows: [],
        podcastEpisodes: podcastEpisodes,
        trendingPodcasts: [],
        popularClubs: [],
        dynamicRails: dynamicRails,
        railPlan: railPlan
    )
}

private func makeDynamicItem(
    id: Int,
    reason: String,
    performer: Components.Schemas.HomeFeedDynamicRailPerformer? = nil
) -> Components.Schemas.HomeFeedDynamicRailItem {
    .init(
        id: id,
        show: makeShow(id),
        performer: performer,
        reason: .init(
            kind: "just_passing_through",
            label: reason,
            evidence: .init()
        )
    )
}

private func makeEpisode(id: Int) -> Components.Schemas.HomeFeedPodcastEpisode {
    .init(
        id: id,
        title: "A Fresh Set",
        releaseDate: Date(timeIntervalSince1970: 1_786_003_200),
        podcast: .init(id: 91, slug: "the-green-room", title: "The Green Room"),
        recommendation: .init(
            reason: .guestAppearance,
            comedian: .init(
                id: 81,
                uuid: "avery-stone",
                name: "Avery Stone",
                imageUrl: ""
            ),
            appearanceRole: .guest,
            followedComedian: false,
            favoritePodcast: false
        )
    )
}

private func makeShow(_ id: Int) -> Components.Schemas.Show {
    .init(
        id: id,
        clubId: 301,
        clubName: "New York Comedy Club",
        date: Date(timeIntervalSince1970: 1_786_003_200),
        tickets: [],
        name: "Show \(id)",
        socialData: nil,
        lineup: [],
        description: nil,
        address: "241 E 24th St, New York, NY",
        room: nil,
        imageUrl: "",
        soldOut: false,
        distanceMiles: nil
    )
}

private func queryValue(_ name: String, from path: String?) -> String? {
    guard let path,
          let components = URLComponents(string: "https://example.com\(path)") else { return nil }
    return components.queryItems?.first(where: { $0.name == name })?.value
}
