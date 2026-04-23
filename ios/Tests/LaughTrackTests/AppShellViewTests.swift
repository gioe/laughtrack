#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("App shell")
@MainActor
struct AppShellViewTests {
    @Test("shell renders four top-level tabs")
    func shellRendersTabs() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-tabs")
        let host = HostedView(
            AppShellView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environmentObject(authManager)
        )

        try host.requireText("Home")
        try host.requireText("Search")
        try host.requireText("Activity")
        try host.requireText("Profile")
    }
}
#endif
