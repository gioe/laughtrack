#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("Settings favorites view")
@MainActor
struct SettingsFavoritesViewTests {
    @Test("signed-in settings view loads saved favorites from the live API contract")
    func signedInSettingsLoadsSavedFavorites() async throws {
        let nearbyStore = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "settings-favorites")
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "settings-favorites"
        )
        let favorites = ComedianFavoriteStore()
        let host = HostedView(
            SettingsView(
                apiClient: makeClient(
                    response: .success(
                        .init(
                            data: [
                                .init(
                                    id: 101,
                                    uuid: "comedian-uuid-1",
                                    name: "Taylor Tomlinson",
                                    imageUrl: "https://example.com/taylor.png",
                                    socialData: .init(id: 101),
                                    showCount: 5,
                                    isFavorite: true
                                )
                            ]
                        )
                    )
                ),
                signedOutMessage: nil,
                nearbyPreferenceStore: nearbyStore
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsFavoritesSection)
        try host.requireText("Nearby defaults")
        try host.requireLabel("Taylor Tomlinson")
        try host.requireLabel("5 tracked show appearances")
    }

    @Test("signed-out settings view reaches auth UI before any favorites fetch runs")
    func signedOutSettingsSkipsFavoritesFetch() async throws {
        let nearbyStore = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "settings-signed-out")
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "settings-signed-out")
        let favorites = ComedianFavoriteStore()
        let recorder = FavoritesRequestRecorder()
        let host = HostedView(
            SettingsView(
                apiClient: makeClient(response: .recorder(recorder)),
                signedOutMessage: nil,
                nearbyPreferenceStore: nearbyStore
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
        )

        try host.requireLabel("Sign in to sync your favorites.")
        try host.requireText("Nearby defaults")
        #expect(recorder.getFavoritesCalls == 0)
    }

    private func makeClient(response: MockSettingsFavoritesTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockSettingsFavoritesTransport(response: response)
        )
    }
}

private final class FavoritesRequestRecorder: @unchecked Sendable {
    var getFavoritesCalls = 0
}

private struct MockSettingsFavoritesTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.FavoriteListResponse)
        case recorder(FavoritesRequestRecorder)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch response {
        case .success(let payload):
            if operationID == "getFavorites" {
                let encoder = JSONEncoder()
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(payload))
                )
            }
        case .recorder(let recorder):
            if operationID == "getFavorites" {
                recorder.getFavoritesCalls += 1
            }
        }

        return (
            HTTPResponse(
                status: .internalServerError,
                headerFields: [.contentType: "application/json"]
            ),
            HTTPBody(#"{"error":"unexpected operation"}"#)
        )
    }
}
#endif
