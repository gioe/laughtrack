#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("Profile view", .disabled("TASK-1761: HostedView UI assertions need refresh — see TASK-1740 follow-up"))
@MainActor
struct ProfileViewTests {
    @Test("profile keeps nearby defaults but adopts compact section framing")
    func profileUsesCompactSectionFraming() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .environmentObject(ComedianFavoriteStore())
                .environmentObject(authManager)
        )

        try host.requireText("Your comedy setup")
        try host.requireText("Profile")
        try host.requireText("Nearby defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsFavoritesSection)
    }
}
#endif
