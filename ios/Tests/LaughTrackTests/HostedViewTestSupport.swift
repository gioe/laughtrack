#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import UIKit
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackCore

@MainActor
enum LaughTrackHostedViewTestSupport {
    static func makeClient() -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: FailingTransport()
        )
    }

    static func makeNearbyPreferenceStore(name: String) -> NearbyPreferenceStore {
        let suiteName = "LaughTrackHostedViewTestSupport.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults))
    }

    static func makeNearbyLocationResolver() -> any NearbyLocationResolving {
        StubNearbyLocationResolver()
    }

    static func makeNearbyLocationController(
        store: NearbyPreferenceStore,
        resolver: (any NearbyLocationResolving)? = nil
    ) -> NearbyLocationController {
        NearbyLocationController(store: store, resolver: resolver ?? StubNearbyLocationResolver())
    }

    static func makeServiceContainer(name: String) -> ServiceContainer {
        let store = makeNearbyPreferenceStore(name: name)
        let resolver = makeNearbyLocationResolver()
        let controller = NearbyLocationController(store: store, resolver: resolver)
        let container = ServiceContainer()
        container.register(NearbyPreferenceStore.self, scope: .appLevel, instance: store)
        container.register((any NearbyLocationResolving).self, scope: .appLevel, instance: resolver)
        container.register(NearbyLocationController.self, scope: .appLevel, instance: controller)
        return container
    }

    static func makeAuthManager(name: String) async -> AuthManager {
        let secureStorage = InMemorySecureStorage()
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let appStateStorage = AppStateStorage(
            userDefaults: UserDefaults(suiteName: "LaughTrackHostedViewTestSupport.auth.\(name).\(UUID().uuidString)")!
        )
        let manager = AuthManager(
            tokenManager: AuthTokenManager(secureStorage: secureStorage),
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: MockOAuthSessionRunner()
        )
        await manager.restoreSession()
        return manager
    }

    static func makeAuthenticatedAuthManager(
        name: String,
        provider: AuthProvider = .apple,
        expiresAt: Date = Date().addingTimeInterval(60 * 60)
    ) async -> AuthManager {
        let secureStorage = InMemorySecureStorage()
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let appStateStorage = AppStateStorage(
            userDefaults: UserDefaults(suiteName: "LaughTrackHostedViewTestSupport.authenticated.\(name).\(UUID().uuidString)")!
        )
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: MockOAuthSessionRunner()
        )

        let accessToken = makeAccessToken(expiresAt: expiresAt)
        // AuthManager.restoreSession (post-TASK-1724) clears the session when access ==
        // refresh, treating it as a pre-rotation install. Use distinct tokens so the
        // restored state is .authenticated, not .signedOut.
        let refreshToken = makeAccessToken(expiresAt: expiresAt.addingTimeInterval(60))
        try? tokenManager.storeTokens(accessToken: accessToken, refreshToken: refreshToken)
        appStateStorage.setValue(
            AuthSessionMetadata(
                provider: provider,
                signedInAt: Date(),
                expiresAt: expiresAt
            ),
            forKey: "laughtrack.auth.session-metadata"
        )

        await manager.restoreSession()
        return manager
    }

    private static func makeAccessToken(expiresAt: Date) -> String {
        let header = ["alg": "HS256", "typ": "JWT"]
        let payload = ["exp": Int(expiresAt.timeIntervalSince1970)]

        return [
            base64URL(header),
            base64URL(payload),
            "signature",
        ].joined(separator: ".")
    }

    private static func base64URL(_ object: [String: Any]) -> String {
        let data = try! JSONSerialization.data(withJSONObject: object)
        return data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

@MainActor
final class StubNearbyLocationResolver: NearbyLocationResolving {
    func requestCurrentZip() async throws -> String {
        throw NearbyLocationError.unavailable
    }
}

private struct FailingTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        throw URLError(.notConnectedToInternet)
    }
}

private final class MockOAuthSessionRunner: OAuthSessionRunning {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        URL(string: "\(callbackScheme)://auth/callback")!
    }
}

private final class InMemorySecureStorage: SecureStorageProtocol {
    private var values: [String: String] = [:]

    func save(_ value: String, forKey key: String) throws {
        values[key] = value
    }

    func retrieve(forKey key: String) throws -> String? {
        values[key]
    }

    func delete(forKey key: String) throws {
        values[key] = nil
    }

    func deleteAll() throws {
        values.removeAll()
    }
}

@MainActor
final class HostedView {
    // Under iOS 26 / Xcode 26, only the *first* UIWindow that calls `makeKeyAndVisible`
    // in a test process reliably wires SwiftUI's accessibility tree onto its hosting
    // controller's UIView hierarchy. Subsequent fresh windows render visually but the
    // accessibility identifiers and accessibility-element children never appear under
    // UIView traversal — every assertion that depends on those reads then fails.
    // Reuse the same UIWindow across tests, swapping in a fresh UIHostingController
    // each time so each test gets an isolated SwiftUI environment but the accessibility
    // wiring stays put.
    private static var sharedWindow: UIWindow?

    private let window: UIWindow
    private let hostingController: UIHostingController<AnyView>

    init<Content: View>(_ rootView: Content) {
        if let existingWindow = HostedView.sharedWindow {
            window = existingWindow
        } else {
            window = UIWindow(frame: UIScreen.main.bounds)
            HostedView.sharedWindow = window
            window.makeKeyAndVisible()
        }
        hostingController = UIHostingController(rootView: AnyView(rootView))
        window.rootViewController = hostingController
        render()
    }

    func render() {
        hostingController.view.frame = window.bounds
        hostingController.view.setNeedsLayout()
        hostingController.view.layoutIfNeeded()
        pumpRunLoop()
    }

    func findView(withIdentifier identifier: String) -> UIView? {
        findView(in: hostingController.view, withIdentifier: identifier)
    }

    @discardableResult
    func requireView(withIdentifier identifier: String) throws -> UIView {
        try waitUntil("Missing view with accessibility identifier '\(identifier)'") {
            findView(withIdentifier: identifier)
        }
    }

    @discardableResult
    func requireLabel(_ text: String) throws -> UIView {
        try waitUntil("Missing label with text '\(text)'") {
            findText(in: hostingController.view, text: text)
        }
    }

    @discardableResult
    func requireText(_ text: String) throws -> UIView {
        try waitUntil("Missing text '\(text)'") {
            findText(in: hostingController.view, text: text)
        }
    }

    func tapControl(withIdentifier identifier: String) throws {
        let view = try requireView(withIdentifier: identifier)
        guard
            let control = (view as? UIControl) ??
                sequence(first: view.superview, next: { $0?.superview }).compactMap({ $0 as? UIControl }).first
        else {
            Issue.record("View '\(identifier)' is not backed by a UIControl")
            return
        }

        control.sendActions(for: .touchUpInside)
        render()
    }

    private func waitUntil<T>(
        _ message: String,
        timeout: TimeInterval = 1.5,
        locator: () -> T?
    ) throws -> T {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if let value = locator() {
                return value
            }
            pumpRunLoop()
        }
        Issue.record("\(message)")
        throw NSError(domain: "HostedView", code: 1, userInfo: [NSLocalizedDescriptionKey: message])
    }

    private func pumpRunLoop() {
        RunLoop.main.run(until: Date().addingTimeInterval(0.02))
    }

    private func findView(in root: UIView, withIdentifier identifier: String) -> UIView? {
        if root.accessibilityIdentifier == identifier {
            return root
        }

        if let elements = root.accessibilityElements {
            for element in elements {
                if (element as AnyObject).accessibilityIdentifier == identifier {
                    return (element as? UIView) ?? root
                }
            }
        }

        for subview in root.subviews {
            if let match = findView(in: subview, withIdentifier: identifier) {
                return match
            }
        }

        return nil
    }

    private func findText(in root: UIView, text: String) -> UIView? {
        if let label = root as? UILabel, label.text == text {
            return label
        }

        if let button = root as? UIButton {
            if button.titleLabel?.text == text {
                return button
            }
            if #available(iOS 15.0, *), button.configuration?.title == text {
                return button
            }
        }

        if root.accessibilityLabel == text {
            return root
        }

        // SwiftUI on iOS 26 exposes Text() and Button labels through synthetic
        // accessibility elements attached to a parent UIView's accessibilityElements
        // array — they are not rendered as UILabel / UIButton subviews. Each synthetic
        // element's accessibilityLabel carries the visible text.
        if let elements = root.accessibilityElements {
            for element in elements {
                if (element as AnyObject).accessibilityLabel == text {
                    return (element as? UIView) ?? root
                }
            }
        }

        for subview in root.subviews {
            if let match = findText(in: subview, text: text) {
                return match
            }
        }

        return nil
    }
}
#endif
