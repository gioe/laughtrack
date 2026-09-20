import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Detail hero layout")
@MainActor
struct DetailHeroLayoutTests {
    @Test("detail hero keeps media landscape and below most of a phone viewport")
    func detailHeroUsesCompactLandscapeMedia() {
        #expect(DetailHeroLayout.imageAspectRatio >= 1.45)
        #expect(DetailHeroLayout.maximumMediaHeight <= 280)
        #expect(DetailHeroLayout.mediaHeight(forWidth: 390) <= 280)
    }

    @Test("detail hero action layout stays compact enough for title clearance")
    func detailHeroActionLayoutIsCompact() {
        #expect(DetailHeroLayout.actionDiameter <= 40)
        #expect(DetailHeroLayout.actionLabelVerticalGap <= 3)
        #expect(DetailHeroLayout.contentSpacingWithActions <= 8)
    }

    @Test("detail hero protects overlay text against variable headshot brightness")
    func detailHeroProtectsOverlayTextContrast() {
        #expect(DetailHeroLayout.bottomScrimOpacity >= 0.9)
        #expect(DetailHeroLayout.heroTextShadowOpacity >= 0.7)
    }

    // The solo-headliner title fixture that previously lived here moved to
    // ShowTitlePresentationTests — `ShowTitlePresentation.title(for:)` rendering is
    // not a hero-layout concern, and keeping a parallel copy here is what shipped a
    // stale expectation (TASK-2536). See TASK-2537.

    @Test("show detail hero omits countdown badges")
    func showHeroBadgeOmitsCountdown() {
        let show = Self.showDetail()
        let badges = ShowDetailPresentation.heroBadges(for: show)

        #expect(badges.isEmpty)
    }

    @Test("show detail summary facts include event operations")
    func showSummaryFactsIncludeOperationalDetails() {
        let show = Self.showDetail()

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Room", "Address", "Distance", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "$30.00")
        #expect(facts.first { $0.label == "Venue" }?.value == "Comedy Cellar")
        #expect(facts.first { $0.label == "Distance" }?.value == "2.1 miles away")
    }

    @Test("show detail summary facts omit missing optional values and retain address")
    func showSummaryFactsOmitMissingValuesAndRetainAddress() {
        var show = Self.showDetail()
        show.tickets = nil
        show.room = nil
        show.distanceMiles = nil
        show.address = "117 MacDougal St, New York, NY"
        show.club.address = "117 MacDougal St, New York, NY"

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Address", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "Price unavailable")
    }

    @Test("show detail ticket cell targets ticket purchase URL")
    func showTicketCellTargetsTicketPurchaseURL() {
        var show = Self.showDetail()
        show.cta = .init(url: "https://laughtrack.app/show-cta", label: "Buy tickets", isSoldOut: false)

        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://laughtrack.app/tickets")
    }

    @Test("show detail calendar event uses show venue and ticket URL")
    func showCalendarEventUsesShowVenueAndTicketURL() {
        let show = Self.showDetail()

        let event = ShowCalendarEventPresentation.event(for: show)

        #expect(event.title == "Mark Normand and Friends")
        #expect(event.startDate == show.date)
        #expect(event.endDate == show.date.addingTimeInterval(2 * 60 * 60))
        #expect(event.location?.contains("Comedy Cellar") == true)
        #expect(event.url?.absoluteString == "https://laughtrack.app/tickets")
    }

    @Test("show detail preserves available source description")
    func showDetailPreservesSourceDescription() {
        let show = Self.showDetail()

        #expect(ShowDetailPresentation.eventDescription(for: show) == show.description?.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private static func showDetail() -> Components.Schemas.ShowDetail {
        .init(
            id: 301,
            clubName: "Comedy Cellar",
            date: Date(timeIntervalSince1970: 1_779_705_000),
            tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/tickets", soldOut: false, _type: "General admission")],
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: nil,
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: 2.1,
            timezone: "America/New_York",
            showPageUrl: "https://laughtrack.app/show",
            club: .init(
                id: 201,
                name: "Comedy Cellar",
                address: "117 MacDougal St, New York, NY",
                imageUrl: "https://example.com/club.png",
                timezone: "America/New_York"
            ),
            cta: .init(url: "https://laughtrack.app/tickets", label: "Buy tickets", isSoldOut: false)
        )
    }
}


#if canImport(UIKit)
import SwiftUI
import UIKit
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
@testable import LaughTrackCore

/// Actual detail routes rendered with stable API fixtures at three layout sizes.
/// Snapshot files are review artifacts, not pixel-golden assertions.
@Suite("Detail hierarchy captures", .serialized)
@MainActor
struct DetailHierarchyCaptureTests {
    @Test("capture detail routes at compact and regular widths", arguments: ["small", "large", "tablet"])
    func captureHierarchy(profile: String) async throws {
        let size = profile == "small" ? CGSize(width: 375, height: 667)
            : profile == "large" ? CGSize(width: 430, height: 932)
            : CGSize(width: 1024, height: 1366)
        let payloads = try makePayloads()
        for route in ["show", "club", "comedian", "podcast", "episode"] {
            let transport = StubClientTransport { request, _, _, _ in
                let path = URLComponents(string: request.path ?? "")?.path ?? ""
                let key = path.replacingOccurrences(of: "/api/v1/", with: "").trimmingCharacters(in: CharacterSet(charactersIn: "/"))
                let data = try #require(payloads[key], "Unexpected capture request: \(path)")
                return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(data))
            }
            let client = Client(serverURL: URL(string: "https://example.com/api/v1")!, configuration: .laughTrack, transport: transport)
            let auth = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "hierarchy-\(route)")
            let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "hierarchy-\(route)")
            let defaults = UserDefaults(suiteName: "hierarchy-\(UUID().uuidString)")!
            let queue = OfflineOperationQueue<LaughTrackOfflineOperation>(storageKey: "saved", userDefaults: defaults, networkMonitor: NetworkMonitor.shared, executor: { _ in })
            container.register(SavedShowStore.self, scope: .appLevel, instance: SavedShowStore(cache: DataCache<LaughTrackCacheKey>(), persistentCache: LaughTrackHostedViewTestSupport.makePersistentMainPageCache(name: "hierarchy-saved"), offlineQueue: queue))
            let screen: AnyView
            let expectedOperation: String
            switch route {
            case "show": screen = AnyView(ShowDetailView(showID: 201, apiClient: client)); expectedOperation = "getShow"
            case "club": screen = AnyView(ClubDetailView(clubId: 202, apiClient: client)); expectedOperation = "getClub"
            case "comedian": screen = AnyView(ComedianDetailView(comedianID: 301, apiClient: client)); expectedOperation = "getComedian"
            case "podcast": screen = AnyView(PodcastDetailView(podcastID: 401, apiClient: client)); expectedOperation = "getPodcast"
            default: screen = AnyView(PodcastEpisodeDetailView(episodeID: 501, apiClient: client)); expectedOperation = "getPodcastEpisode"
            }
            let host = HostedView(NavigationStack { screen }
                .environmentObject(TypedNavigationCoordinator<AppRoute>())
                .environmentObject(auth)
                .environmentObject(ComedianFavoriteStore())
                .environmentObject(ClubFavoriteStore())
                .environmentObject(PodcastFavoriteStore())
                .environmentObject(PodcastPlaybackController())
                .environmentObject(LoginModalPresenter())
                .environmentObject(LaughTrackHostedViewTestSupport.makeSoftPushPromptCoordinator(name: "hierarchy"))
                .environment(\.serviceContainer, container)
                .environment(\.scenePhase, .active)
                .environment(\.horizontalSizeClass, profile == "tablet" ? .regular : .compact),
                freshWindow: true, viewportSize: size)
            await host.settle(iterations: 60)
            #expect(transport.capturedRequests.contains { $0.operationID == expectedOperation })
            let image = try host.snapshot()
            #expect(image.size == size)
            let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4024-\(profile)-\(route).png")
            try #require(image.pngData()).write(to: output)
            print("Detail hierarchy capture: \(output.path)")
        }
    }

    private func makePayloads() throws -> [String: Data] {
        // Captured from the canonical screenshot fixture. Show dates are advanced
        // per run so this harness continues to exercise upcoming ticket actions.
        let raw = Data(Self.fixtureJSON.utf8)
        let object = try #require(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        let date = ISO8601DateFormatter().string(from: Date().addingTimeInterval(3600))
        func refreshDates(_ value: Any) -> Any {
            if let values = value as? [Any] { return values.map(refreshDates) }
            if let values = value as? [String: Any] {
                return values.mapValues(refreshDates).merging(values["date"] == nil ? [:] : ["date": date]) { _, new in new }
            }
            return value
        }
        return try object.mapValues { try JSONSerialization.data(withJSONObject: refreshDates($0)) }
    }

    private static let fixtureJSON = #"""
{"shows/201":{"data":{"id":201,"clubId":202,"date":"2026-08-16T20:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Taylor Tomlinson & Friends","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/201","soldOut":false,"type":"General Admission"}],"lineup":[{"id":302,"uuid":"fixture-302","name":"Taylor Tomlinson","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","showCount":40,"socialData":{"id":302,"instagramAccount":"taylortomlinson","website":"https://example.invalid/taylortomlinson","popularity":98},"isFavorite":false}],"showPageUrl":"https://example.invalid/show/201","club":{"id":202,"name":"Comedy Cellar","imageUrl":"https://laughtrack.b-cdn.net/clubs/Comedy%20Cellar%20New%20York.png","address":"117 MacDougal St, New York, NY","timezone":"America/New_York"},"cta":{"label":"Buy tickets","isSoldOut":false,"url":"https://example.invalid/tickets/201"},"description":"A special night of new material and surprise guests."},"relatedShows":[]},"clubs/202":{"data":{"id":202,"name":"Comedy Cellar","imageUrl":"https://laughtrack.b-cdn.net/clubs/Comedy%20Cellar%20New%20York.png","heroImageUrl":"https://laughtrack.b-cdn.net/clubs/Comedy%20Cellar%20New%20York.png","website":"https://www.comedycellar.com","address":"117 MacDougal St, New York, NY 10012","zipCode":"10012","phoneNumber":"(212) 254-3480"}},"clubs/202/highlights":{"data":{"tonightShows":[{"id":201,"clubId":202,"date":"2026-08-16T20:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Taylor Tomlinson & Friends","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/201","soldOut":false,"type":"General Admission"}],"lineup":[{"id":302,"uuid":"fixture-302","name":"Taylor Tomlinson","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","showCount":40,"socialData":{"id":302,"instagramAccount":"taylortomlinson","website":"https://example.invalid/taylortomlinson","popularity":98},"isFavorite":false}]},{"id":206,"clubId":202,"date":"2026-08-16T19:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Ali Wong: Live","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/206","soldOut":false,"type":"General Admission"}],"lineup":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","showCount":36,"socialData":{"id":301,"instagramAccount":"aliwong","website":"https://example.invalid/aliwong","popularity":96},"isFavorite":false}]},{"id":207,"clubId":202,"date":"2026-08-16T21:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Andrew Schulz: New Material","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/207","soldOut":false,"type":"General Admission"}],"lineup":[{"id":303,"uuid":"fixture-303","name":"Andrew Schulz","imageUrl":"https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png","showCount":34,"socialData":{"id":303,"instagramAccount":"andrewschulz","website":"https://example.invalid/andrewschulz","popularity":94},"isFavorite":false}]}],"nextShow":{"id":202,"clubId":202,"date":"2026-08-17T21:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/clubs/Comedy%20Cellar%20New%20York.png","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Taylor Tomlinson & Friends","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/202","soldOut":false,"type":"General Admission"}],"lineup":[]},"frequentPerformers":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","socialData":{"id":301,"instagramAccount":"aliwong","website":"https://example.invalid/aliwong"},"showCount":28,"isFavorite":false},{"id":302,"uuid":"fixture-302","name":"Taylor Tomlinson","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","socialData":{"id":302,"instagramAccount":"taylortomlinson","website":"https://example.invalid/taylortomlinson"},"showCount":27,"isFavorite":false},{"id":303,"uuid":"fixture-303","name":"Andrew Schulz","imageUrl":"https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png","socialData":{"id":303,"instagramAccount":"andrewschulz","website":"https://example.invalid/andrewschulz"},"showCount":26,"isFavorite":false}]}},"shows/search":{"data":[{"id":201,"clubId":202,"date":"2026-08-16T20:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Taylor Tomlinson & Friends","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/201","soldOut":false,"type":"General Admission"}],"lineup":[{"id":302,"uuid":"fixture-302","name":"Taylor Tomlinson","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","showCount":40,"socialData":{"id":302,"instagramAccount":"taylortomlinson","website":"https://example.invalid/taylortomlinson","popularity":98},"isFavorite":false}]},{"id":206,"clubId":202,"date":"2026-08-16T19:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Ali Wong: Live","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/206","soldOut":false,"type":"General Admission"}],"lineup":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","showCount":36,"socialData":{"id":301,"instagramAccount":"aliwong","website":"https://example.invalid/aliwong","popularity":96},"isFavorite":false}]},{"id":207,"clubId":202,"date":"2026-08-16T21:00:00-04:00","imageUrl":"https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png","clubName":"Comedy Cellar","clubCity":"New York","clubState":"NY","name":"Andrew Schulz: New Material","room":"Main Room","timezone":"America/New_York","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/207","soldOut":false,"type":"General Admission"}],"lineup":[{"id":303,"uuid":"fixture-303","name":"Andrew Schulz","imageUrl":"https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png","showCount":34,"socialData":{"id":303,"instagramAccount":"andrewschulz","website":"https://example.invalid/andrewschulz","popularity":94},"isFavorite":false}]}],"total":45,"filters":[],"zipCapTriggered":false},"comedians/301":{"data":{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","socialData":{"id":301,"instagramAccount":"aliwong","website":"https://example.invalid/aliwong"},"podcastAppearances":[],"homeLocation":{"city":"San Francisco","state":"CA","country":"US"}}},"comedians/301/upcoming-runs":{"data":[{"clubId":201,"clubName":"Hollywood Improv","clubImageUrl":"https://laughtrack.b-cdn.net/clubs/Hollywood%20Improv.png","shows":[{"id":106,"clubId":201,"date":"2026-08-17T20:00:00-07:00","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","clubName":"Hollywood Improv","clubCity":"Hollywood","clubState":"CA","name":"Ali Wong: Live","room":"Main Room","timezone":"America/Los_Angeles","soldOut":false,"tickets":[{"price":40,"purchaseUrl":"https://example.invalid/tickets/106","soldOut":false,"type":"General Admission"}],"lineup":[{"id":302,"uuid":"fixture-302","name":"Taylor Tomlinson","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg","showCount":40,"socialData":{"id":302,"instagramAccount":"taylortomlinson","website":"https://example.invalid/taylortomlinson","popularity":98},"isFavorite":false}]}]}]},"comedians/301/co-bill":{"data":[]},"comedians/past-shows":{"data":[],"total":0},"podcasts/401":{"podcast":{"id":401,"slug":"history-hyenas","title":"History Hyenas","episodeCount":130,"hosts":[{"id":304,"uuid":"fixture-304","name":"Chris Distefano","imageUrl":"https://laughtrack.b-cdn.net/comedians/Chris%20Distefano.png"},{"id":305,"uuid":"fixture-305","name":"Yannis Pappas","imageUrl":"https://laughtrack.b-cdn.net/comedians/Yannis%20Pappas.png"}],"authorName":"Chris Distefano & Yannis Pappas","websiteUrl":"https://example.invalid/podcasts/history-hyenas","feedUrl":"https://example.invalid/feeds/history-hyenas","imageUrl":"https://megaphone.imgix.net/podcasts/48030056-989d-11ef-a614-3bc2f8865178/image/171a69e4231342ccae610db68861892b.jpeg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg","description":"Comedians tear through history's strangest characters, rivalries, and disasters.","isFavorite":false},"episodes":[{"id":501,"title":"Watch Your Tone with Ryan Sickler | History Hyenas","description":"The boys sit down with comedian Ryan Sickler to discuss his new comedy special, near death experiences, and how to monitor your tone when talking your significant other. Check out his new special Live and Alive here: https://www.youtube.com/watch?v=PMGWVyM2NJo","releaseDate":"2025-10-23T19:00:00.000Z","durationSeconds":4654,"episodeUrl":null,"audioUrl":"https://pdst.fm/e/pfx.vpixl.com/u8u9X/pscrb.fm/rss/p/mgln.ai/e/1118/clrtpod.com/m/arttrk.com/p/YMH00/traffic.megaphone.fm/YMH7734324090.mp3?updated=1730821365","appearances":[{"id":304,"uuid":"fixture-304","name":"Chris Distefano","imageUrl":"https://laughtrack.b-cdn.net/comedians/Chris%20Distefano.png"},{"id":305,"uuid":"fixture-305","name":"Yannis Pappas","imageUrl":"https://laughtrack.b-cdn.net/comedians/Yannis%20Pappas.png"},{"id":249148,"uuid":"6713c3fbed5bc17713cca3ba90ecd5b0","name":"Ryan Sickler","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/249148/8d0ef3db-606f-4357-84a3-9eee79a9d3b2/avatar.jpg"}]}],"relatedComedians":[{"id":301,"uuid":"fixture-301","name":"Ali Wong","imageUrl":"https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png","socialData":{"id":301,"instagramAccount":"aliwong","website":"https://example.invalid/aliwong"},"showCount":28,"isFavorite":false}]},"podcast-episodes/501":{"podcast":{"id":401,"slug":"history-hyenas","title":"History Hyenas","episodeCount":130,"hosts":[{"id":304,"uuid":"fixture-304","name":"Chris Distefano","imageUrl":"https://laughtrack.b-cdn.net/comedians/Chris%20Distefano.png"},{"id":305,"uuid":"fixture-305","name":"Yannis Pappas","imageUrl":"https://laughtrack.b-cdn.net/comedians/Yannis%20Pappas.png"}],"authorName":"Chris Distefano & Yannis Pappas","websiteUrl":"https://example.invalid/podcasts/history-hyenas","feedUrl":"https://example.invalid/feeds/history-hyenas","imageUrl":"https://megaphone.imgix.net/podcasts/48030056-989d-11ef-a614-3bc2f8865178/image/171a69e4231342ccae610db68861892b.jpeg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg","description":"Comedians tear through history's strangest characters, rivalries, and disasters.","isFavorite":false},"episode":{"id":501,"title":"Watch Your Tone with Ryan Sickler | History Hyenas","description":"The boys sit down with comedian Ryan Sickler to discuss his new comedy special, near death experiences, and how to monitor your tone when talking your significant other. Check out his new special Live and Alive here: https://www.youtube.com/watch?v=PMGWVyM2NJo","releaseDate":"2025-10-23T19:00:00.000Z","durationSeconds":4654,"episodeUrl":null,"audioUrl":"https://pdst.fm/e/pfx.vpixl.com/u8u9X/pscrb.fm/rss/p/mgln.ai/e/1118/clrtpod.com/m/arttrk.com/p/YMH00/traffic.megaphone.fm/YMH7734324090.mp3?updated=1730821365","appearances":[{"id":304,"uuid":"fixture-304","name":"Chris Distefano","imageUrl":"https://laughtrack.b-cdn.net/comedians/Chris%20Distefano.png"},{"id":305,"uuid":"fixture-305","name":"Yannis Pappas","imageUrl":"https://laughtrack.b-cdn.net/comedians/Yannis%20Pappas.png"},{"id":249148,"uuid":"6713c3fbed5bc17713cca3ba90ecd5b0","name":"Ryan Sickler","imageUrl":"https://laughtrack.b-cdn.net/comedian-images/249148/8d0ef3db-606f-4357-84a3-9eee79a9d3b2/avatar.jpg"}]}}}
"""#
}
#endif
