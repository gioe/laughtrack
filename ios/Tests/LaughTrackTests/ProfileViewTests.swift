#if canImport(UIKit)
import SwiftUI
import Testing
@testable import LaughTrackApp

@Suite("Profile view")
@MainActor
struct ProfileViewTests {
    @Test("profile tab renders favorites and nearby defaults")
    func profileTabRendersProfileView() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile")
        let host = HostedView(
            ProfileView(apiClient: LaughTrackHostedViewTestSupport.makeClient(), signedOutMessage: nil)
                .environment(\.appTheme, LaughTrackTheme())
                .environmentObject(authManager)
        )

        try host.requireText("Nearby defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsFavoritesSection)
    }
}
#endif
