import Foundation
import LaughTrackAPIClient

public enum LoadFailure: Error, Equatable, Sendable {
    case network(String)
    case decoding(String)
    case badParams(String)
    case unauthorized(String)
    case rateLimited(retryAfter: TimeInterval?, message: String?)
    case serverError(status: Int, message: String?)
    case unexpected(status: Int, message: String?)

    public var message: String {
        switch self {
        case .network(let message):
            return message
        case .decoding(let message):
            return message
        case .badParams(let message):
            return "\(message) (HTTP 400)"
        case .unauthorized(let message):
            return "\(message) (HTTP 401)"
        case .rateLimited(let retryAfter, let message):
            let base = message ?? "LaughTrack is busy right now."
            let hint: String
            if let retryAfter, retryAfter > 0 {
                let seconds = Int(retryAfter.rounded(.up))
                hint = "Please try again in \(seconds) second\(seconds == 1 ? "" : "s")."
            } else {
                hint = "Please try again in a moment."
            }
            return "\(base) \(hint) (HTTP 429)"
        case .serverError(let status, let message):
            let base = message ?? "LaughTrack hit a server error. Please retry in a moment."
            return "\(base) (HTTP \(status))"
        case .unexpected(let status, let message):
            let base = message ?? "LaughTrack returned an unexpected response."
            return status > 0 ? "\(base) (HTTP \(status))" : base
        }
    }

    public var defaultTitle: String {
        switch self {
        case .network:
            return "No connection"
        case .decoding:
            return "Data issue"
        case .badParams:
            return "Check these filters"
        case .unauthorized:
            return "Sign in required"
        case .rateLimited:
            return "Too many requests"
        case .serverError:
            return "Server hiccup"
        case .unexpected:
            return "Unexpected response"
        }
    }

    public enum RecoveryAction: Equatable {
        case retry
        case signIn
    }

    public var recoveryAction: RecoveryAction {
        switch self {
        case .unauthorized:
            return .signIn
        case .network, .decoding, .badParams, .rateLimited, .serverError, .unexpected:
            return .retry
        }
    }
}

public func classifyRequestError(_ error: any Error, context: String, networkMessage: String) -> LoadFailure {
    if isLaughTrackResponseDecodingError(error) {
        return .decoding("LaughTrack reached \(context), but could not read the response. Please try again.")
    }
    return .network(networkMessage)
}

public func classifyUndocumented(status: Int, context: String) -> LoadFailure {
    switch status {
    case 401:
        return .unauthorized("Sign in to load \(context).")
    case 400:
        return .badParams("LaughTrack could not apply those \(context) filters.")
    case 429:
        return .rateLimited(retryAfter: nil, message: "LaughTrack is rate-limiting \(context) right now.")
    case 500..<600:
        return .serverError(status: status, message: nil)
    default:
        return .unexpected(status: status, message: "LaughTrack returned an unexpected \(context) response.")
    }
}
