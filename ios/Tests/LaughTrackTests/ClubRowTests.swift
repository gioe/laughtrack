import Testing
import Foundation
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Club row")
struct ClubRowTests {
    @Test("club row keeps location subtitle content")
    func clubRowKeepsLocationSubtitleContent() {
        let club = makeClub(city: "San Francisco", state: "CA", address: "444 Battery St")

        #expect(ClubRow.subtitle(for: club) == "San Francisco, CA")
    }

    @Test("club row falls back to address when city and state are absent")
    func clubRowFallsBackToAddress() {
        let club = makeClub(city: nil, state: nil, address: "444 Battery St")

        #expect(ClubRow.subtitle(for: club) == "444 Battery St")
    }

    @Test("club row keeps existing count metadata")
    func clubRowKeepsExistingCountMetadata() {
        let club = makeClub(activeComedianCount: 19, showCount: 8)

        #expect(ClubRow.metadata(for: club) == ["19 active comedians", "8 shows"])
    }

    @Test("browse entity rows fit club artwork without cropping")
    func browseEntityRowsFitClubArtworkWithoutCropping() throws {
        let source = try String(contentsOf: browseComponentsSourceURL(), encoding: .utf8)
        let block = try sourceBlock(
            in: source,
            from: "struct LaughTrackEntityRow: View",
            to: "private var artworkBackground: some View"
        )

        #expect(block.contains(".scaledToFit()"))
        #expect(!block.contains(".scaledToFill()"))
    }

    private func makeClub(
        city: String? = "San Francisco",
        state: String? = "CA",
        address: String? = "444 Battery St",
        activeComedianCount: Int? = 19,
        showCount: Int? = 8
    ) -> Components.Schemas.ClubSearchItem {
        Components.Schemas.ClubSearchItem(
            id: 1,
            address: address,
            name: "Punch Line Comedy Club",
            zipCode: "94111",
            imageUrl: "",
            showCount: showCount,
            isFavorite: nil,
            city: city,
            state: state,
            phoneNumber: nil,
            socialData: nil,
            activeComedianCount: activeComedianCount,
            distanceMiles: nil
        )
    }

    private func browseComponentsSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/DesignSystem/LaughTrackBrowseComponents.swift")
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
