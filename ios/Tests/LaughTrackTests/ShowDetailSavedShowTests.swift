import Foundation
import Testing
@testable import LaughTrackApp

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
        #expect(source.contains("show: ShowDetailPresentation.savedShowRow(for: show)"))
    }

    @Test("show detail supports accessible save and unsave feedback")
    func supportsAccessibleSaveAndUnsave() throws {
        let source = try showDetailSource()

        #expect(source.contains("store.setSaved("))
        #expect(source.contains("isSaved: !isSaved"))
        #expect(source.contains("store.isPending(show.id)"))
        #expect(source.contains(".disabled(isPending)"))
        #expect(source.contains(#".accessibilityLabel(isSaved ? "Remove from saved shows" : "Save show")"#))
        #expect(source.contains(#".accessibilityValue(isPending ? "Updating" : (isSaved ? "Saved" : "Not saved"))"#))
        #expect(source.contains("case .queued(let saved):"))
        #expect(source.contains("case .signInRequired:"))
        #expect(source.contains("loginModalPresenter.present()"))
        #expect(source.contains("case .failure(let message):"))
    }

    @Test("past shows can only expose an existing saved state")
    func pastShowEligibility() {
        let now = Date(timeIntervalSince1970: 10_000)

        #expect(
            ShowSavedActionPresentation.shouldShow(
                isSaved: false,
                showDate: now.addingTimeInterval(-1),
                now: now
            ) == false
        )
        #expect(
            ShowSavedActionPresentation.shouldShow(
                isSaved: true,
                showDate: now.addingTimeInterval(-1),
                now: now
            )
        )
        #expect(
            ShowSavedActionPresentation.shouldShow(
                isSaved: false,
                showDate: now.addingTimeInterval(1),
                now: now
            )
        )
    }

    @Test("show detail maps to a canonical saved-show row")
    func mapsCanonicalSavedShowRow() {
        let detail = DemoContent.primaryShowDetail.data
        let row = ShowDetailPresentation.savedShowRow(for: detail)

        #expect(row.id == detail.id)
        #expect(row.clubId == detail.club.id)
        #expect(row.clubName == detail.clubName ?? detail.club.name)
        #expect(row.date == detail.date)
        #expect(row.name == detail.name)
        #expect(row.lineup == detail.lineup)
        #expect(row.imageUrl == detail.imageUrl)
        #expect(row.timezone == detail.timezone ?? detail.club.timezone)
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
