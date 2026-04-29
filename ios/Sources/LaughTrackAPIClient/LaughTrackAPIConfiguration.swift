import Foundation
import OpenAPIRuntime

/// Date transcoder for LaughTrack API payloads.
///
/// The web API emits ISO-8601 timestamps with fractional seconds in show payloads
/// and some older endpoints can emit whole-second timestamps. The OpenAPI runtime
/// defaults to whole-second ISO-8601 only, so production clients need this wider
/// decoder for response bodies.
public struct LaughTrackFlexibleISO8601DateTranscoder: DateTranscoder, @unchecked Sendable {
    private let lock = NSLock()
    private let withFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private let withoutFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    public init() {}

    public func encode(_ date: Date) throws -> String {
        lock.lock()
        defer { lock.unlock() }
        return withFractional.string(from: date)
    }

    public func decode(_ dateString: String) throws -> Date {
        lock.lock()
        defer { lock.unlock() }

        if let date = withFractional.date(from: dateString) {
            return date
        }
        if let date = withoutFractional.date(from: dateString) {
            return date
        }

        throw DecodingError.dataCorrupted(
            .init(codingPath: [], debugDescription: "Expected ISO 8601 date string, got: \(dateString)")
        )
    }
}

public extension Configuration {
    static var laughTrack: Configuration {
        .init(dateTranscoder: LaughTrackFlexibleISO8601DateTranscoder())
    }
}

public func isLaughTrackResponseDecodingError(_ error: any Error) -> Bool {
    if error is DecodingError {
        return true
    }

    guard let clientError = error as? ClientError else {
        return false
    }

    return clientError.response != nil && clientError.underlyingError is DecodingError
}
