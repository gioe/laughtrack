import Testing
import Foundation
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Home content sections")
struct HomeContentSectionTests {
    @Test("unfiltered home leads with show rails before comedians and clubs")
    func unfilteredHomeLeadsWithShowRailsBeforeComediansAndClubs() {
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
            .comedians,
            .clubs,
        ])
    }

    @Test("home primitive filters render only their matching content sections")
    func homePrimitiveFiltersRenderOnlyMatchingContentSection() {
        #expect(HomeContentSection.sections(for: .shows) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
        ])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
        #expect(HomeContentSection.sections(for: .podcasts) == [.podcasts])
    }

    @Test("home show hero omits footer actions")
    func homeShowHeroOmitsFooterActions() {
        let show = Components.Schemas.Show(
            id: 801,
            clubID: 301,
            clubName: "Comedy In Harlem",
            date: Date(timeIntervalSince1970: 1_777_590_000),
            tickets: [.init(price: 0, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission")],
            name: "K Smith & Friends",
            socialData: nil,
            lineup: [],
            description: nil,
            address: "750A St Nicholas Ave, New York, NY",
            room: nil,
            imageUrl: "",
            soldOut: false,
            distanceMiles: 10.6
        )

        #expect(HomeShowsTonightHeroPresentation.shouldShowFooter(for: show) == false)
    }

    @Test("home cards use cached async images")
    func homeCardsUseCachedAsyncImages() throws {
        let source = try String(contentsOf: homeViewSourceURL(), encoding: .utf8)

        #expect(!source.contains("\n            AsyncImage(url:"))
        #expect(source.contains("CachedAsyncImage(url:"))
    }

    @Test("home source uses carousel hero grid entity rails and lifted rail copy")
    func homeSourceUsesCarouselHeroGridEntityRailsAndLiftedRailCopy() throws {
        let source = try String(contentsOf: homeViewSourceURL(), encoding: .utf8)

        #expect(source.contains("TabView"))
        #expect(source.contains("PageTabViewStyle"))
        #expect(source.contains("LazyVGrid"))
        #expect(source.contains("Comics on the rise this week"))
        #expect(!source.contains("eyebrow: \"Trending comedians\""))
    }

    private func homeViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Home/Views/HomeView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}
