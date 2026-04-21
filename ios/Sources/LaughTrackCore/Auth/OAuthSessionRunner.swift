import AuthenticationServices
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public enum AuthFlowError: LocalizedError {
    case unableToStart
    case invalidCallback
    case cancelled

    public var errorDescription: String? {
        switch self {
        case .unableToStart:
            "LaughTrack couldn’t open the sign-in session. Please try again."
        case .invalidCallback:
            "LaughTrack didn’t receive a valid sign-in callback."
        case .cancelled:
            "Sign-in was cancelled."
        }
    }
}

public protocol OAuthSessionRunning: AnyObject {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL
}

public final class SystemOAuthSessionRunner: NSObject, OAuthSessionRunning {
    private var session: ASWebAuthenticationSession?

    public override init() {}

    public func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: startURL,
                callbackURLScheme: callbackScheme
            ) { url, error in
                if let error = error as? ASWebAuthenticationSessionError,
                   error.code == .canceledLogin {
                    continuation.resume(throwing: AuthFlowError.cancelled)
                    return
                }

                if let url {
                    continuation.resume(returning: url)
                } else {
                    continuation.resume(throwing: AuthFlowError.invalidCallback)
                }
            }

            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            self.session = session

            guard session.start() else {
                continuation.resume(throwing: AuthFlowError.unableToStart)
                return
            }
        }
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
