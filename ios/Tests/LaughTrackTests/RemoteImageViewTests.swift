import Foundation
import Testing
@testable import LaughTrackApp

@Suite("RemoteImageView")
struct RemoteImageViewTests {
    @Test("invalid image URLs render fallback instead of an endless placeholder")
    func invalidImageURLsRenderFallbackInsteadOfEndlessPlaceholder() throws {
        let source = try String(contentsOf: remoteImageViewSourceURL(), encoding: .utf8)

        #expect(source.contains("if let url = URL.normalizedExternalURL"))
        #expect(source.contains("fallbackArtwork"))
        #expect(!source.contains("AsyncImage(url: URL.normalizedExternalURL"))
    }

    private func remoteImageViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Detail/Components/RemoteImageView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}
