import Foundation
import Testing

@Suite("Show detail saved shows")
struct ShowDetailSavedShowTests {
    @Test("show detail observes and loads saved-show state")
    func observesAndLoadsSavedShowState() throws {
        let source = try showDetailSource()

        #expect(source.contains("@ObservedObject var store: SavedShowStore"))
        #expect(source.contains("serviceContainer.resolve(SavedShowStore.self)"))
        #expect(source.contains("savedShowStore.loadState("))
        #expect(source.contains("guard authManager.currentUser != nil else { return }"))
        #expect(source.contains(".task(id: savedShowLoadKey)"))
    }

    @Test("show detail supports accessible save and unsave feedback")
    func supportsAccessibleSaveAndUnsave() throws {
        let source = try showDetailSource()

        #expect(source.contains("store.setSaved("))
        #expect(source.contains("isSaved: !isSaved"))
        #expect(source.contains("store.isPending(showID)"))
        #expect(source.contains(".disabled(isPending)"))
        #expect(source.contains(#".accessibilityLabel(isSaved ? "Remove from saved shows" : "Save show")"#))
        #expect(source.contains(#".accessibilityValue(isPending ? "Updating" : (isSaved ? "Saved" : "Not saved"))"#))
        #expect(source.contains("case .queued(let saved):"))
        #expect(source.contains("case .signInRequired:"))
        #expect(source.contains("loginModalPresenter.present()"))
        #expect(source.contains("case .failure(let message):"))
    }

    private func showDetailSource(filePath: String = #filePath) throws -> String {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Detail/Views/ShowDetailView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return try String(contentsOf: sourceURL, encoding: .utf8)
    }
}
