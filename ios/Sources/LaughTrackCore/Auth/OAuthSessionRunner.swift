import AuthenticationServices
import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public enum AuthFlowError: LocalizedError {
    case unableToStart
    case invalidCallback
    case cancelled
    case timedOut

    public var errorDescription: String? {
        switch self {
        case .unableToStart:
            "LaughTrack couldn’t open the sign-in session. Please try again."
        case .invalidCallback:
            "LaughTrack didn’t receive a valid sign-in callback."
        case .cancelled:
            "Sign-in was cancelled."
        case .timedOut:
            "Sign-in timed out. Please check your connection and try again."
        }
    }
}

public protocol OAuthSessionRunning: AnyObject {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL
}

public final class SystemOAuthSessionRunner: NSObject, OAuthSessionRunning {
    private var session: ASWebAuthenticationSession?
    private let timeout: TimeInterval

    // Default backstop for a wedged web flow. ASWebAuthenticationSession only
    // surfaces a result on user-cancel or when the laughtrack:// callback fires;
    // a stalled web page (redirect loop, dead network, or an OAuth error that
    // strands on an https page the session can't intercept) would otherwise hang
    // the sheet indefinitely. Long enough to tolerate a slow login + 2FA.
    public init(timeout: TimeInterval = 180) {
        self.timeout = timeout
        super.init()
    }

    public func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let gate = ResumeGate(continuation)

            let session = ASWebAuthenticationSession(
                url: startURL,
                callbackURLScheme: callbackScheme
            ) { url, error in
                if let error = error as? ASWebAuthenticationSessionError,
                   error.code == .canceledLogin {
                    gate.resume(throwing: AuthFlowError.cancelled)
                    return
                }

                if let url {
                    gate.resume(returning: url)
                } else {
                    gate.resume(throwing: AuthFlowError.invalidCallback)
                }
            }

            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            self.session = session

            guard session.start() else {
                gate.resume(throwing: AuthFlowError.unableToStart)
                return
            }

            let timeoutItem = DispatchWorkItem { [weak session] in
                session?.cancel()
                gate.resume(throwing: AuthFlowError.timedOut)
            }
            // First resolution (callback/cancel/timeout) cancels the pending
            // timer so it can't fire a second, ignored result.
            gate.onResolve = { timeoutItem.cancel() }
            DispatchQueue.main.asyncAfter(deadline: .now() + timeout, execute: timeoutItem)
        }
    }
}

// Guarantees a CheckedContinuation is resumed exactly once across the racing
// completion handler and timeout work item — a second resume would crash. The
// first resume runs `onResolve` (timer teardown) before handing back the value.
private final class ResumeGate: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<URL, Error>?
    var onResolve: (() -> Void)?

    init(_ continuation: CheckedContinuation<URL, Error>) {
        self.continuation = continuation
    }

    func resume(returning value: URL) {
        finish { $0.resume(returning: value) }
    }

    func resume(throwing error: Error) {
        finish { $0.resume(throwing: error) }
    }

    private func finish(_ body: (CheckedContinuation<URL, Error>) -> Void) {
        lock.lock()
        guard let continuation else {
            lock.unlock()
            return
        }
        self.continuation = nil
        let cleanup = onResolve
        onResolve = nil
        lock.unlock()

        cleanup?()
        body(continuation)
    }
}

extension SystemOAuthSessionRunner: ASWebAuthenticationPresentationContextProviding {
    public func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        #if canImport(UIKit)
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first(where: \.isKeyWindow) ?? ASPresentationAnchor()
        #elseif canImport(AppKit)
        NSApplication.shared.windows.first ?? ASPresentationAnchor()
        #else
        ASPresentationAnchor()
        #endif
    }
}
