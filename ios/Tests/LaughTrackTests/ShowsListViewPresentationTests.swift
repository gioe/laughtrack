import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Shows list view presentation")
struct ShowsListViewPresentationTests {
    @Test("compact pinned lists label date search without an eyebrow")
    func compactPinnedListsUseClearDateSearchHeading() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)

        #expect(source.contains("LaughTrackSectionHeader(title: \"Search dates\")"))
        #expect(!source.contains("LaughTrackSectionHeader(eyebrow: \"Calendar\""))
    }

    @Test("show search results use compact ticket row presentation")
    func showSearchResultsUseCompactTicketRowPresentation() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let rowBlock = try sourceBlock(
            in: source,
            from: "let standoutShowID = ShowsListStandout.resolveID(in: result.items)",
            to: ".accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))"
        )

        #expect(rowBlock.contains("ShowRow("))
        #expect(rowBlock.contains("let standoutShowID = ShowsListStandout.resolveID(in: result.items)"))
        #expect(rowBlock.contains("show.id == standoutShowID ? .compactTicketProminent : .compactTicket"))
        #expect(rowBlock.contains("AdaptiveSearchResults(spacing: theme.spacing.md)"))
    }

    @Test("standout resolver picks the single highest positive popularity score")
    func standoutResolverPicksSingleHighestPositiveScore() {
        let shows = [
            makeShow(id: 1, popularityScore: 0.2),
            makeShow(id: 2, popularityScore: 0.9),
            makeShow(id: 3, popularityScore: 0.4),
        ]

        #expect(ShowsListStandout.resolveID(in: shows) == 2)
    }

    @Test("standout resolver returns nil when there is no clear positive winner")
    func standoutResolverReturnsNilWithoutClearPositiveWinner() {
        #expect(ShowsListStandout.resolveID(in: [
            makeShow(id: 1, popularityScore: nil),
            makeShow(id: 2, popularityScore: 0),
        ]) == nil)
        #expect(ShowsListStandout.resolveID(in: [
            makeShow(id: 1, popularityScore: 0.8),
            makeShow(id: 2, popularityScore: 0.8),
        ]) == nil)
    }

    private func showsListViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testsURL = URL(fileURLWithPath: filePath)
        let iosRoot = testsURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return iosRoot.appendingPathComponent("Sources/LaughTrackApp/Search/Views/ShowsListView.swift")
    }

    private func sourceBlock(in source: String, from start: String, to end: String) throws -> String {
        guard let startRange = source.range(of: start) else {
            throw SourceBlockError.missingStart(start)
        }
        guard let endRange = source[startRange.upperBound...].range(of: end) else {
            throw SourceBlockError.missingEnd(end)
        }
        return String(source[startRange.lowerBound..<endRange.upperBound])
    }

    private enum SourceBlockError: Error {
        case missingStart(String)
        case missingEnd(String)
    }

    private func makeShow(id: Int, popularityScore: Double?) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: id,
            clubId: 20,
            date: Date(timeIntervalSince1970: 1_710_000_000),
            name: "Show \(id)",
            popularityScore: popularityScore,
            imageUrl: "https://example.com/show-\(id).jpg"
        )
    }
}
