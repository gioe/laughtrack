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
    @Test("first content waits for mounted content and emits once with bounded network timing")
    func firstContentMeasurement() async throws {
        var now: TimeInterval = 100
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache(), uptime: { now })
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: nil)
        #expect(model.contentDidAppear(for: key) == nil)
        await refresh(model, client: planClient(feed: orderedFeed()), session: nil, cacheTTL: 60)
        now = 100.125
        let parameters = try #require(model.contentDidAppear(for: key))
        #expect(parameters["first_content_ms"] as? Double == 125)
        #expect(parameters["source"] as? String == "network")
        #expect(parameters["account"] as? String == "anonymous")
        #expect(parameters["server_feed_total_ms"] as? Double == 12.5)
        #expect(parameters["client_load_ms"] is Double)
        #expect(parameters["server_shows_tonight_ms"] as? Double == 8)
        #expect(parameters.count == 6)
        let trace = try JSONSerialization.data(withJSONObject: parameters, options: [.sortedKeys])
        print("TASK4036_FIRST_CONTENT_TRACE " + String(decoding: trace, as: UTF8.self))
        #expect(model.contentDidAppear(for: key) == nil)
        await refresh(model, client: planClient(feed: orderedFeed()), session: nil, cacheTTL: 60)
        #expect(model.contentDidAppear(for: key) == nil)
    }

    @Test("memory plan reuse is measured without attributing an unrelated network response")
    func memoryFirstContentMeasurement() async throws {
        let cache = HomeDiscoverRailPlanCache()
        let first = HomeDiscoverRailPlanModel(planCache: cache)
        await refresh(first, client: planClient(feed: orderedFeed()), cacheTTL: 60)
        let model = HomeDiscoverRailPlanModel(planCache: cache)
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        let gate = PlanResponseGate()
        let pending = Task { await refresh(model, client: planClient(feed: orderedFeed(), gate: gate)) }
        await gate.waitUntilRequested()
        let parameters = model.contentDidAppear(for: key)
        #expect(parameters?["source"] as? String == "in_memory")
        #expect(parameters?["account"] as? String == "authenticated")
        #expect(parameters?.count == 3)
        await gate.release()
        await pending.value
        #expect(model.contentDidAppear(for: key) == nil)
    }

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
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())

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
        let shows = (1...7).map { makeShow($0) }
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
            label: "Rarely nearby",
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

    @Test("Episodes for you is limited to five items and Rarely nearby to eight")
    func requestedRailsUseTheirItemLimits() throws {
        let episodes = (1...7).map(makeEpisode)
        let passingThroughItems = (11...20).map {
            makeDynamicItem(id: $0, reason: "Comic \($0) is visiting")
        }
        let feed = makeFeed(
            podcastEpisodes: episodes,
            dynamicRails: [
                .init(
                    railKey: "just_passing_through",
                    label: "Rarely nearby",
                    items: passingThroughItems
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
                    itemIds: passingThroughItems.map { String($0.id) }
                )
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .podcastEpisodes(let limitedEpisodes) = sections[0].content,
              case .dynamicShows(_, let limitedPassingThrough) = sections[1].content else {
            Issue.record("Expected podcast and featured dynamic rails")
            return
        }

        #expect(limitedEpisodes.map(\.id) == [1, 2, 3, 4, 5])
        #expect(limitedPassingThrough.map(\.id) == [11, 12, 13, 14, 15, 16, 17, 18])
    }

    @Test("removed dynamic rails are ignored")
    func removedDynamicRailsAreIgnored() {
        let item = makeDynamicItem(id: 9, reason: "Three comedians")
        for railKey in ["stacked_lineups", "rare_returns", "only_chance_nearby"] {
            let feed = makeFeed(
                dynamicRails: [
                    .init(
                        railKey: railKey,
                        label: railKey,
                        items: [item]
                    )
                ],
                railPlan: makePlan(rails: [
                    .init(
                        railKey: railKey,
                        payloadKey: "dynamicRails",
                        position: 0,
                        itemIds: ["9"]
                    )
                ])
            )

            #expect(HomeDiscoverRailPlanPresentation.sections(from: feed) == [])
        }
    }

    @Test("custom show rails use Today-style cards and feature their associated comedian")
    func customShowRailsUseTodayStyleCards() {
        let item = makeDynamicItem(
            id: 9,
            reason: "Avery is visiting",
            performer: .init(id: 81, uuid: "avery-stone", name: "Avery Stone")
        )

        for railKey in [
            "just_passing_through",
            "starting_to_buzz",
            "from_your_podcasts",
        ] {
            #expect(HomeDiscoverRailPlanPresentation.usesTodayStyleShowCarousel(railKey: railKey))
            #expect(
                HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                    railKey: railKey,
                    item: item
                ) == 81
            )
        }
        #expect(
            HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                railKey: "only_chance_nearby",
                item: item
            ) == nil
        )
        #expect(!HomeDiscoverRailPlanPresentation.usesTodayStyleShowCarousel(
            railKey: "because_you_follow_them"
        ))
        #expect(
            HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                railKey: "rare_returns",
                item: item
            ) == nil
        )
    }

    @Test("shows tonight is limited to eight planned shows")
    func showsTonightIsLimitedToEightPlannedShows() throws {
        let shows = (1...10).map { makeShow($0) }
        let feed = makeFeed(
            showsTonight: shows,
            railPlan: makePlan(rails: [
                .init(
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 0,
                    itemIds: shows.map { String($0.id) }
                )
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .showsTonight(let limitedShows) = sections[0].content else {
            Issue.record("Expected shows-tonight rail")
            return
        }
        #expect(limitedShows.map(\.id) == [1, 2, 3, 4, 5, 6, 7, 8])
    }

    @Test("followed comedian shows are capped and feature the favorite lineup member")
    func followedComedianShowsAreCappedAndFeatureFavorite() throws {
        let favorite = Components.Schemas.ComedianLineup(
            name: "Avery Stone",
            imageUrl: "",
            uuid: "avery-stone",
            id: 81,
            isFavorite: true
        )
        let shows = (1...10).map { id in
            makeShow(id, lineup: id == 1 ? [favorite] : [])
        }
        let feed = makeFeed(
            followedComedianShows: shows,
            railPlan: makePlan(rails: [
                .init(
                    railKey: "followed_comedian_shows",
                    payloadKey: "followedComedianShows",
                    position: 0,
                    itemIds: shows.map { String($0.id) }
                )
            ])
        )

        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: feed))
        guard case .followedComedianShows(let limitedShows) = sections[0].content else {
            Issue.record("Expected followed-comedian shows")
            return
        }
        #expect(limitedShows.map(\.id) == [1, 2, 3, 4, 5, 6, 7, 8])
        #expect(HomeDiscoverRailPlanPresentation.preferredFavoriteHeadlinerID(show: limitedShows[0]) == 81)
    }

    @Test("uncached loading stays pending until the feed resolves")
    func uncachedLoadingStaysPending() async {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        #expect(model.presentation(for: key) == .pending)
        let gate = PlanResponseGate()
        let pending = Task { await refresh(model, client: planClient(gate: gate)) }
        await gate.waitUntilRequested()
        #expect(model.presentation(for: key) == .pending)
        await gate.release()
        await pending.value
        #expect(model.presentation(for: key) == .legacy)
    }

    @Test("cached server order survives model recreation and a failed refresh")
    func cachedOrderSurvivesRecreationAndFailure() async throws {
        let cache = HomeDiscoverRailPlanCache()
        let original = HomeDiscoverRailPlanModel(planCache: cache)
        await refresh(original, client: planClient(feed: orderedFeed()), cacheTTL: 60)
        let previous = try #require(original.sections)
        let key = original.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        let restored = HomeDiscoverRailPlanModel(planCache: cache)
        #expect(restored.presentation(for: key) == .planned(previous))
        let otherKeys = [
            restored.requestKey(zipCode: "94103", distanceMiles: 25, sessionDiscriminator: "account-a|session"),
            restored.requestKey(zipCode: "10012", distanceMiles: 50, sessionDiscriminator: "account-a|session"),
            restored.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-b|session"),
            restored.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|new-session"),
            restored.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: nil),
        ]
        for otherKey in otherKeys {
            #expect(restored.presentation(for: otherKey) == .pending)
            // This also protects the render before SwiftUI starts refresh.
            #expect(original.presentation(for: otherKey) == .pending)
        }
        let gate = PlanResponseGate()
        let pending = Task { await refresh(restored, client: planClient(gate: gate)) }
        await gate.waitUntilRequested()
        #expect(restored.presentation(for: key) == .planned(previous))
        await gate.release()
        await pending.value
        #expect(restored.presentation(for: key) == .planned(previous))
    }

    @Test("invalidated and nonpositive-lifetime plans are not reused")
    func invalidatedPlansAreNotReused() throws {
        let cache = HomeDiscoverRailPlanCache()
        let model = HomeDiscoverRailPlanModel(planCache: cache)
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        let sections = try #require(HomeDiscoverRailPlanPresentation.sections(from: orderedFeed()))
        cache.store(sections, for: key, ttl: 60)
        #expect(model.presentation(for: key) == .planned(sections))
        cache.store(nil, for: key, ttl: 60)
        #expect(model.presentation(for: key) == .pending)
        for ttl in [0.0, -1.0] {
            cache.store(sections, for: key, ttl: ttl)
            #expect(model.presentation(for: key) == .pending)
        }
    }

    @Test("empty plans replace prior content while unsupported plans use the legacy fallback")
    func emptyAndUnsupportedPlansHaveDistinctOutcomes() async {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        await refresh(model, client: planClient(feed: orderedFeed()))
        await refresh(model, client: planClient(feed: makeFeed(railPlan: makePlan(rails: []))))
        #expect(model.presentation(for: key) == .planned([]))
        await refresh(model, client: planClient(feed: makeFeed(railPlan: makePlan(version: 2, rails: []))))
        #expect(model.presentation(for: key) == .legacy)
    }

    @Test("failed refresh retains the last valid server rail order")
    func failedRefreshRetainsServerOrder() async throws {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        await refresh(model, client: planClient(feed: orderedFeed()))
        let previous = try #require(model.sections)
        #expect(previous.map(\.id) == ["followed_comedian_shows", "shows_tonight"])

        let gate = PlanResponseGate()
        let pending = Task {
            await refresh(model, client: planClient(gate: gate))
        }
        await gate.waitUntilRequested()
        #expect(model.sections == previous)
        await gate.release()
        await pending.value
        #expect(model.sections == previous)
    }

    @Test("changed location or session hides the previous personalized plan while pending", arguments: [false, true])
    func changedScopeHidesPreviousPlan(changesSession: Bool) async throws {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        await refresh(model, client: planClient(feed: orderedFeed()))
        _ = try #require(model.sections)
        let gate = PlanResponseGate()
        let pending = Task {
            await refresh(
                model,
                client: planClient(gate: gate),
                zipCode: changesSession ? "10012" : "94103",
                session: changesSession ? "account-b|new-session" : "account-a|session"
            )
        }
        await gate.waitUntilRequested()
        #expect(model.sections == nil)
        await gate.release()
        await pending.value
        #expect(model.sections == nil)
    }

    @Test("a late response cannot restore a previous location or session plan", arguments: [false, true])
    func lateResponseCannotRestorePreviousScope(changesSession: Bool) async throws {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let gate = PlanResponseGate()
        let previousRequest = Task {
            await refresh(model, client: planClient(feed: orderedFeed(), gate: gate))
        }
        await gate.waitUntilRequested()
        let emptyFeed = makeFeed(railPlan: makePlan(rails: []))
        await refresh(
            model,
            client: planClient(feed: emptyFeed),
            zipCode: changesSession ? "10012" : "94103",
            session: changesSession ? "account-b|new-session" : "account-a|session"
        )
        #expect(model.sections == [])
        await gate.release()
        await previousRequest.value
        #expect(model.sections == [])
    }

    @Test("fresh cache instance renders public rails while the server plan is suspended", arguments: ["account-b|session", "signed-out"])
    func persistedPublicRailsRenderBeforeNetwork(session: String) async throws {
        let directory = try launchCacheDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let writer = PersistentMainPageCache(directory: directory)
        await writer.setHomeFeed(orderedFeed(), zipCode: "10012", distanceMiles: 25, ttl: 60)
        // No shared model, plan cache, or in-memory feed survives this boundary.
        let reader = PersistentMainPageCache(directory: directory)
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let discriminator: String? = session == "signed-out" ? nil : session
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: discriminator)
        let gate = PlanResponseGate()
        let pending = Task {
            await refresh(model, client: planClient(feed: orderedFeed(), gate: gate), session: discriminator, persistentCache: reader)
        }
        await gate.waitUntilRequested()
        guard case .planned(let cached) = model.presentation(for: key) else {
            await gate.release()
            await pending.value
            Issue.record("Persisted public content must render before the response")
            return
        }
        #expect(cached.map(\.id) == ["shows_tonight"])
        #expect(model.hasResolved)
        #expect(model.isRefreshing)
        #expect(model.failure(for: key) == nil)
        let parameters = model.contentDidAppear(for: key)
        #expect(parameters?["source"] as? String == "persisted_cache")
        #expect(parameters?.count == 3)
        await gate.release()
        await pending.value
        #expect(model.contentDidAppear(for: key) == nil)
        #expect(model.sections?.map(\.id) == ["followed_comedian_shows", "shows_tonight"])
        #expect(!model.isRefreshing)
        #expect(model.failure(for: key) == nil)
    }

    @Test("invalid persisted public feeds stay pending during the network request", arguments: ["zip", "radius", "expired", "schema", "empty"])
    func invalidLaunchCacheStaysPending(reason: String) async throws {
        let directory = try launchCacheDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let writer = PersistentMainPageCache(directory: directory, schemaVersion: "launch-current")
        await writer.setHomeFeed(
            reason == "empty" ? makeFeed() : orderedFeed(),
            zipCode: "10012", distanceMiles: 25, ttl: reason == "expired" ? -1 : 60
        )
        let reader = PersistentMainPageCache(directory: directory, schemaVersion: reason == "schema" ? "launch-next" : "launch-current")
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let zip = reason == "zip" ? "94103" : "10012"
        let radius = reason == "radius" ? 50 : 25
        let key = model.requestKey(zipCode: zip, distanceMiles: radius, sessionDiscriminator: nil)
        let gate = PlanResponseGate()
        let pending = Task {
            await refresh(model, client: planClient(gate: gate), zipCode: zip, session: nil, persistentCache: reader, distanceMiles: radius)
        }
        await gate.waitUntilRequested()
        #expect(model.presentation(for: key) == .pending)
        #expect(!model.hasResolved)
        await gate.release()
        await pending.value
    }

    @Test("offline launch preserves public content and an explicit retry replaces it")
    func offlineLaunchPreservesPublicContentAndRetries() async throws {
        let directory = try launchCacheDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let cache = PersistentMainPageCache(directory: directory)
        await cache.setHomeFeed(orderedFeed(), zipCode: "10012", distanceMiles: 25, ttl: 60)
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: nil)
        await refresh(model, client: planClient(), session: nil, persistentCache: cache)
        #expect(model.sections?.map(\.id) == ["shows_tonight"])
        #expect(model.failure(for: key) != nil)
        #expect(!model.isRefreshing)
        await refresh(model, client: planClient(feed: makeFeed(railPlan: makePlan(rails: []))), session: nil, persistentCache: cache, forceRefresh: true)
        #expect(model.presentation(for: key) == .planned([]))
        #expect(model.failure(for: key) == nil)
        #expect(!model.isRefreshing)
    }

    @Test("cancelled launch response cannot replace the public fallback")
    func cancelledLaunchKeepsPublicFallback() async throws {
        let directory = try launchCacheDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let cache = PersistentMainPageCache(directory: directory)
        await cache.setHomeFeed(orderedFeed(), zipCode: "10012", distanceMiles: 25, ttl: 60)
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let gate = PlanResponseGate()
        let pending = Task {
            await refresh(model, client: planClient(feed: orderedFeed(), gate: gate), persistentCache: cache)
        }
        await gate.waitUntilRequested()
        #expect(model.sections?.map(\.id) == ["shows_tonight"])
        pending.cancel()
        await gate.release()
        await pending.value
        let key = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        #expect(model.contentDidAppear(for: key) == nil)
        #expect(model.sections?.map(\.id) == ["shows_tonight"])
        #expect(!model.isRefreshing)
    }

    @Test("an already cancelled refresh cannot clear the current context")
    func alreadyCancelledRefreshCannotClearCurrentContext() async throws {
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        await refresh(model, client: planClient(feed: orderedFeed()))
        let currentSections = try #require(model.sections)
        let currentKey = model.requestKey(zipCode: "10012", distanceMiles: 25, sessionDiscriminator: "account-a|session")
        let stale = Task {
            // Cancellation is established before refresh starts, independently
            // of task scheduling or whether a transport honors cancellation.
            withUnsafeCurrentTask { $0?.cancel() }
            #expect(Task.isCancelled)
            await refresh(model, client: planClient(), zipCode: "94103", session: "account-b|session")
        }
        await stale.value
        #expect(model.sections == currentSections)
        #expect(model.presentation(for: currentKey) == .planned(currentSections))
        #expect(model.hasResolved)
        #expect(!model.isRefreshing)
        #expect(model.failure(for: currentKey) == nil)
    }

    @Test("a previous launch refresh cannot restore content after the location changes")
    func lateLaunchResponseCannotRestorePreviousLocation() async throws {
        let directory = try launchCacheDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let cache = PersistentMainPageCache(directory: directory)
        await cache.setHomeFeed(orderedFeed(), zipCode: "10012", distanceMiles: 25, ttl: 60)
        let model = HomeDiscoverRailPlanModel(planCache: HomeDiscoverRailPlanCache())
        let gate = PlanResponseGate()
        let previous = Task {
            await refresh(model, client: planClient(feed: orderedFeed(), gate: gate), persistentCache: cache)
        }
        await gate.waitUntilRequested()
        #expect(model.sections?.map(\.id) == ["shows_tonight"])
        await refresh(model, client: planClient(feed: makeFeed(railPlan: makePlan(rails: []))), zipCode: "94103", persistentCache: cache)
        #expect(model.sections == [])
        await gate.release()
        await previous.value
        #expect(model.sections == [])
        #expect(!model.isRefreshing)
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
        #expect(plannedRail.contains("usesTodayStyleShowCarousel(railKey: section.id)"))
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
    followedComedianShows: [Components.Schemas.Show] = [],
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
        followedComedianShows: followedComedianShows,
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

private func makeShow(
    _ id: Int,
    lineup: [Components.Schemas.ComedianLineup] = []
) -> Components.Schemas.Show {
    .init(
        id: id,
        clubId: 301,
        clubName: "New York Comedy Club",
        date: Date(timeIntervalSince1970: 1_786_003_200),
        tickets: [],
        name: "Show \(id)",
        socialData: nil,
        lineup: lineup,
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

// A suspended transport makes pending-state assertions deterministic, without
// sleeps or relying on cancellation from SwiftUI's task modifier.
private actor PlanResponseGate {
    private var requested = false
    private var requestWaiter: CheckedContinuation<Void, Never>?
    private var responseWaiter: CheckedContinuation<Void, Never>?

    func suspendResponse() async {
        requested = true
        requestWaiter?.resume()
        requestWaiter = nil
        await withCheckedContinuation { responseWaiter = $0 }
    }

    func waitUntilRequested() async {
        guard !requested else { return }
        await withCheckedContinuation { requestWaiter = $0 }
    }

    func release() {
        responseWaiter?.resume()
        responseWaiter = nil
    }
}

private func orderedFeed() -> Components.Schemas.HomeFeed {
    makeFeed(
        showsTonight: [makeShow(1)],
        followedComedianShows: [makeShow(2)],
        railPlan: makePlan(rails: [
            .init(railKey: "shows_tonight", payloadKey: "showsTonight", position: 2, itemIds: ["1"]),
            .init(railKey: "followed_comedian_shows", payloadKey: "followedComedianShows", position: 1, itemIds: ["2"]),
        ])
    )
}

private func planClient(
    feed: Components.Schemas.HomeFeed? = nil,
    gate: PlanResponseGate? = nil
) -> Client {
    let transport = StubClientTransport { _, _, _, _ in
        await gate?.suspendResponse()
        guard let feed else { throw URLError(.notConnectedToInternet) }
        let data = try APIMockEncoder.make().encode(Components.Schemas.HomeFeedResponse(data: feed))
        return (
            HTTPResponse(status: .ok, headerFields: [.contentType: "application/json", HTTPField.Name("Server-Timing")!: "feed_total;dur=12.5;desc=success, shows_tonight;dur=8;desc=success"]),
            HTTPBody(data)
        )
    }
    return Client(serverURL: URL(string: "https://example.com")!, configuration: .laughTrack, transport: transport, middlewares: [DiscoverTimingMiddleware()])
}

@MainActor
private func refresh(
    _ model: HomeDiscoverRailPlanModel,
    client: Client,
    zipCode: String = "10012",
    session: String? = "account-a|session",
    cacheTTL: TimeInterval = 0,
    persistentCache: PersistentMainPageCache? = nil,
    distanceMiles: Int = 25,
    forceRefresh: Bool = false
) async {
    await model.refresh(
        apiClient: client,
        zipCode: zipCode,
        distanceMiles: distanceMiles,
        sessionDiscriminator: session,
        cache: nil,
        cacheTTL: cacheTTL,
        persistentCache: persistentCache,
        coalescer: HomeFeedRequestCoalescer(),
        forceRefresh: forceRefresh
    )
}

private func launchCacheDirectory() throws -> URL {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    return directory
}
