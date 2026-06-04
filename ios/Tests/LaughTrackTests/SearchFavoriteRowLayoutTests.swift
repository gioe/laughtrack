import Foundation
import Testing

@Suite("Search favorite row layout")
struct SearchFavoriteRowLayoutTests {
    @Test("comedian search favorite button is integrated into the entity row")
    func comedianSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "ComediansDiscoveryView.swift"), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct ComedianRow: View", to: "static func upcomingShowsText")

        #expect(block.contains("action: openDetail"))
        #expect(block.contains("trailingAccessory: {"))
        #expect(block.contains("FavoriteButton("))
        #expect(!block.contains("HStack(spacing: theme.spacing.md)"))
    }

    @Test("podcast search favorite button is integrated into the entity row")
    func podcastSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "PodcastSearchView.swift"), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct PodcastSearchRow: View", to: "private func toggle")

        #expect(block.contains("action: rowAction"))
        #expect(block.contains("private func openPodcastDetail()"))
        #expect(block.contains("trailingAccessory: {"))
        #expect(block.contains("FavoriteButton("))
        #expect(!block.contains("HStack(spacing: theme.spacing.md)"))
    }

    private func searchViewSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Search/Views/\(fileName)")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func sourceBlock(in source: String, from startMarker: String, to endMarker: String) throws -> String {
        guard
            let start = source.range(of: startMarker),
            let end = source.range(of: endMarker, range: start.upperBound..<source.endIndex)
        else {
            throw CocoaError(.fileReadCorruptFile)
        }

        return String(source[start.lowerBound..<end.lowerBound])
    }
}
