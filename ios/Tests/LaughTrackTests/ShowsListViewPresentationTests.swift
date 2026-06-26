import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Shows list view presentation")
struct ShowsListViewPresentationTests {
    @Test("show search results use compact ticket row presentation")
    func showSearchResultsUseCompactTicketRowPresentation() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let rowBlock = try sourceBlock(
            in: source,
            from: "ForEach(result.items, id: \\.id) { show in",
            to: ".accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))"
        )

        #expect(rowBlock.contains("ShowRow("))
        #expect(rowBlock.contains("presentation: .compactTicket"))
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
}
