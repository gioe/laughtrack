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
    private let window: UIWindow
    private let hostingController: UIHostingController<AnyView>

    init<Content: View>(_ rootView: Content) {
        window = UIWindow(frame: UIScreen.main.bounds)
        hostingController = UIHostingController(rootView: AnyView(rootView))
        window.rootViewController = hostingController
        window.makeKeyAndVisible()
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

    func requireView(withIdentifier identifier: String) throws -> UIView {
        try waitUntil("Missing view with accessibility identifier '\(identifier)'") {
            findView(withIdentifier: identifier)
        }
    }

    func requireLabel(_ text: String) throws -> UILabel {
        try waitUntil("Missing label with text '\(text)'") {
            findLabel(in: hostingController.view, text: text)
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
        Issue.record(message)
        throw NSError(domain: "HostedView", code: 1, userInfo: [NSLocalizedDescriptionKey: message])
    }

    private func pumpRunLoop() {
        RunLoop.main.run(until: Date().addingTimeInterval(0.02))
    }

    private func findView(in root: UIView, withIdentifier identifier: String) -> UIView? {
        if root.accessibilityIdentifier == identifier {
            return root
        }

        for subview in root.subviews {
            if let match = findView(in: subview, withIdentifier: identifier) {
                return match
            }
        }

        return nil
    }

    private func findLabel(in root: UIView, text: String) -> UILabel? {
        if let label = root as? UILabel, label.text == text {
            return label
        }

        for subview in root.subviews {
            if let match = findLabel(in: subview, text: text) {
                return match
            }
        }

        return nil
    }
}
#endif
