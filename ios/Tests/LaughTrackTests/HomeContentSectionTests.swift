import Testing
import Foundation
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Home content sections")
struct HomeContentSectionTests {
    @Test("unfiltered home includes shows comedians and clubs")
    func unfilteredHomeIncludesShowsComediansAndClubs() {
        #expect(HomeContentSection.sections(for: nil) == [
            .shows,
            .favoriteShows,
            .comedians,
            .clubs,
        ])
    }

    @Test("home primitive filters render only their matching content section")
    func homePrimitiveFiltersRenderOnlyMatchingContentSection() {
        #expect(HomeContentSection.sections(for: .shows) == [.shows])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
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

    private func homeViewSourceURL() throws -> URL {
        var directory = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        while directory.path != "/" {
            let candidate = directory
                .appendingPathComponent("Sources/LaughTrackApp/Home/Views/HomeView.swift")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return candidate
            }
            directory.deleteLastPathComponent()
        }
        throw CocoaError(.fileNoSuchFile)
    }
}
