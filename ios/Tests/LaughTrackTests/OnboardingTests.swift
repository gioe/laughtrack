import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Onboarding")
@MainActor
struct OnboardingTests {
    @Test("incomplete authenticated users route to onboarding only after profile load")
    func incompleteAuthenticatedUsersRouteToOnboardingAfterProfileLoad() {
        let session = AuthSessionMetadata(provider: .apple, signedInAt: Date(), expiresAt: nil)
        let incompleteUser = AuthenticatedUser(
            displayName: "Maya",
            email: "maya@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: false
        )

        #expect(ContentView.rootSurface(
            authState: .authenticated(session),
            hasLoadedCurrentUser: false,
            currentUser: incompleteUser
        ) == .loading)
        #expect(ContentView.rootSurface(
            authState: .authenticated(session),
            hasLoadedCurrentUser: true,
            currentUser: incompleteUser
        ) == .comedianOnboarding)
    }

    @Test("completed and signed-out users bypass comedian onboarding")
    func completedAndSignedOutUsersBypassComedianOnboarding() {
        let session = AuthSessionMetadata(provider: .apple, signedInAt: Date(), expiresAt: nil)
        let completedUser = AuthenticatedUser(
            displayName: "Maya",
            email: "maya@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: true
        )
        let incompleteUser = AuthenticatedUser(
            displayName: "Maya",
            email: "maya@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: false
        )

        #expect(ContentView.rootSurface(
            authState: .authenticated(session),
            hasLoadedCurrentUser: true,
            currentUser: completedUser
        ) == .authenticatedShell)
        #expect(ContentView.rootSurface(
            authState: .signedOut(message: nil),
            hasLoadedCurrentUser: true,
            currentUser: incompleteUser
        ) == .signedOutShell(message: nil))
    }

    @Test("first-auth incomplete users are gated before the home shell")
    func incompleteAuthenticatedUsersAreGated() {
        let incompleteUser = AuthenticatedUser(
            displayName: "Maya",
            email: "maya@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: false
        )
        let completedUser = AuthenticatedUser(
            displayName: "Maya",
            email: "maya@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: true
        )

        #expect(ContentView.shouldPresentComedianOnboarding(
            authState: .authenticated(.init(provider: .apple, signedInAt: Date(), expiresAt: nil)),
            currentUser: incompleteUser
        ))
        #expect(!ContentView.shouldPresentComedianOnboarding(
            authState: .authenticated(.init(provider: .apple, signedInAt: Date(), expiresAt: nil)),
            currentUser: completedUser
        ))
        #expect(!ContentView.shouldPresentComedianOnboarding(
            authState: .signedOut(message: nil),
            currentUser: incompleteUser
        ))
    }

    @Test("authenticated users wait for profile load before shell decisions")
    func authenticatedUsersWaitForProfileLoadBeforeShellDecisions() async {
        let manager = await makeAuthenticatedAuthManager(loadUserRequest: {
            try await Task.sleep(nanoseconds: 20_000_000)
            return AuthenticatedUser(
                displayName: "Maya",
                email: "maya@example.com",
                avatarURL: nil,
                comedianOnboardingCompleted: false
            )
        })

        let loadTask = Task {
            await manager.refreshCurrentUser()
        }

        await Task.yield()
        #expect(!manager.hasLoadedCurrentUser)

        await loadTask.value
        #expect(manager.hasLoadedCurrentUser)
        #expect(ContentView.shouldPresentComedianOnboarding(
            authState: manager.state,
            currentUser: manager.currentUser
        ))
    }

    @Test("onboarding loads popular comedians before search")
    func loadsPopularComediansInitially() async throws {
        let recorder = OnboardingRequestRecorder()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockOnboardingTransport(recorder: recorder)
        )
        let model = ComedianOnboardingModel()

        await model.loadInitialComedians(apiClient: apiClient, favorites: ComedianFavoriteStore())

        #expect(model.comedians.map(\.name) == ["Taylor Tomlinson", "Sam Morril", "Atsuko Okatsuka"])
        #expect(await recorder.searchQueries == [""])
    }

    @Test("onboarding searches for more comedians")
    func searchesForMoreComedians() async throws {
        let recorder = OnboardingRequestRecorder()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockOnboardingTransport(recorder: recorder)
        )
        let model = ComedianOnboardingModel()

        await model.search("nate", apiClient: apiClient, favorites: ComedianFavoriteStore())

        #expect(model.comedians.map(\.name) == ["Nate Bargatze"])
        #expect(await recorder.searchQueries == ["nate"])
    }

    @Test("users can favorite any number of comedians and still see a target of 3")
    func favoritesAnyNumberWithSuggestedTarget() async throws {
        let recorder = OnboardingRequestRecorder()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockOnboardingTransport(recorder: recorder)
        )
        let favorites = ComedianFavoriteStore()
        let model = ComedianOnboardingModel()
        await model.loadInitialComedians(apiClient: apiClient, favorites: favorites)
        let authManager = await makeAuthenticatedAuthManager()

        await model.toggleFavorite(uuid: "comedian-1", apiClient: apiClient, favorites: favorites, authManager: authManager)
        await model.toggleFavorite(uuid: "comedian-2", apiClient: apiClient, favorites: favorites, authManager: authManager)

        #expect(model.suggestedFavoriteTarget == 3)
        #expect(model.favoriteCount == 2)
        #expect(model.canContinue)
        #expect(favorites.value(for: "comedian-1"))
        #expect(favorites.value(for: "comedian-2"))
        #expect(await recorder.favoriteRequests == ["comedian-1", "comedian-2"])
    }

    @Test("notification step persists preferences and asks the injected push permission boundary")
    func notificationStepStoresPreferencesAndRequestsPushPermission() async throws {
        let permissionRequester = RecordingPushPermissionRequester(result: true)
        let store = NotificationPreferenceStore(appStateStorage: makeStorage(name: "notification-step"))
        let model = ComedianOnboardingModel(pushPermissionRequester: permissionRequester)

        await model.setNotificationPreferences(
            emailEnabled: true,
            pushEnabled: true,
            store: store
        )

        #expect(store.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(store.preferences.favoriteComedianPushAlertsEnabled)
        #expect(await permissionRequester.requestCount == 1)
    }

    @Test("complete and skip both mark server onboarding complete")
    func completeAndSkipMarkServerState() async throws {
        let recorder = OnboardingRequestRecorder()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockOnboardingTransport(recorder: recorder)
        )
        let model = ComedianOnboardingModel()

        await model.complete(apiClient: apiClient, authManager: await makeAuthenticatedAuthManager())
        await model.skip(apiClient: apiClient, authManager: await makeAuthenticatedAuthManager())

        #expect(await recorder.updateMeCalls == 2)
    }

    private func makeAuthenticatedAuthManager(
        loadUserRequest: AuthManager.LoadUserRequest? = nil
    ) async -> AuthManager {
        let secureStorage = InMemorySecureStorage()
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "OnboardingTests.auth.\(UUID().uuidString)")!)
        let expiresAt = Date().addingTimeInterval(60 * 60)
        try? tokenManager.storeTokens(
            accessToken: makeAccessToken(expiresAt: expiresAt),
            refreshToken: makeAccessToken(expiresAt: expiresAt.addingTimeInterval(60))
        )
        appStateStorage.setValue(
            AuthSessionMetadata(provider: .apple, signedInAt: Date(), expiresAt: expiresAt),
            forKey: "laughtrack.auth.session-metadata"
        )
        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: StubOAuthSessionRunner()
        )
        manager.loadUserRequest = loadUserRequest
        await manager.restoreSession()
        return manager
    }

    private func makeAccessToken(expiresAt: Date) -> String {
        let header = ["alg": "HS256", "typ": "JWT"]
        let payload = ["exp": Int(expiresAt.timeIntervalSince1970)]
        return [
            base64URL(header),
            base64URL(payload),
            "signature",
        ].joined(separator: ".")
    }

    private func base64URL(_ object: [String: Any]) -> String {
        let data = try! JSONSerialization.data(withJSONObject: object)
        return data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private func makeStorage(name: String) -> AppStateStorage {
        let suiteName = "OnboardingTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return AppStateStorage(userDefaults: defaults)
    }
}

private actor OnboardingRequestRecorder {
    private(set) var searchQueries: [String] = []
    private(set) var favoriteRequests: [String] = []
    private(set) var updateMeCalls = 0

    func recordSearch(_ query: String) {
        searchQueries.append(query)
    }

    func recordFavorite(_ uuid: String) {
        favoriteRequests.append(uuid)
    }

    func recordUpdateMe() {
        updateMeCalls += 1
    }
}

private struct MockOnboardingTransport: ClientTransport {
    let recorder: OnboardingRequestRecorder

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "searchComedians":
            let query = searchQuery(from: request.path)
            await recorder.recordSearch(query)
            return jsonResponse(Components.Schemas.ComedianSearchResponse(
                data: query == "nate" ? [.comedian(id: 4, uuid: "comedian-4", name: "Nate Bargatze")] : [
                    .comedian(id: 1, uuid: "comedian-1", name: "Taylor Tomlinson"),
                    .comedian(id: 2, uuid: "comedian-2", name: "Sam Morril"),
                    .comedian(id: 3, uuid: "comedian-3", name: "Atsuko Okatsuka"),
                ],
                total: query == "nate" ? 1 : 3,
                filters: []
            ))
        case "addFavorite":
            if let uuid = try? await favoriteUUID(from: body) {
                await recorder.recordFavorite(uuid)
            }
            return jsonResponse(Components.Schemas.FavoriteResponse(data: .init(isFavorited: true)))
        case "updateMe":
            await recorder.recordUpdateMe()
            return jsonResponse(Components.Schemas.MeUpdateResponse(data: .init(comedianOnboardingCompleted: true)))
        default:
            return (
                HTTPResponse(status: .internalServerError, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"unexpected operation"}"#)
            )
        }
    }

    private func searchQuery(from path: String?) -> String {
        guard
            let path,
            let components = URLComponents(string: "https://example.com\(path)")
        else { return "" }

        return components.queryItems?.first(where: { $0.name == "comedian" })?.value ?? ""
    }

    private func favoriteUUID(from body: HTTPBody?) async throws -> String? {
        guard let body else { return nil }
        let data = try await Data(collecting: body, upTo: 1024)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return object?["comedianId"] as? String
    }

    private func jsonResponse<T: Encodable>(_ payload: T) -> (HTTPResponse, HTTPBody?) {
        let body = (try? JSONEncoder().encode(payload)).map(HTTPBody.init)
        return (
            HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
            body
        )
    }
}

private actor RecordingPushPermissionRequester: OnboardingPushPermissionRequesting {
    private let result: Bool
    private(set) var requestCount = 0

    init(result: Bool) {
        self.result = result
    }

    func requestAuthorization() async -> Bool {
        requestCount += 1
        return result
    }
}

private extension Components.Schemas.ComedianSearchItem {
    static func comedian(id: Int, uuid: String, name: String) -> Self {
        .init(
            id: id,
            uuid: uuid,
            name: name,
            imageUrl: "https://example.com/\(uuid).jpg",
            socialData: .init(id: id),
            showCount: 4,
            isFavorite: false
        )
    }
}
