import Foundation
import OpenAPIRuntime

/// Date transcoder for LaughTrack API payloads.
///
/// The web API emits ISO-8601 timestamps with fractional seconds in show payloads
/// and some older endpoints can emit whole-second timestamps. The OpenAPI runtime
/// defaults to whole-second ISO-8601 only, so production clients need this wider
/// decoder for response bodies.
public struct LaughTrackFlexibleISO8601DateTranscoder: DateTranscoder, Sendable {
    public init() {}

    public func encode(_ date: Date) throws -> String {
        LaughTrackISO8601Formatters.shared.string(from: date)
    }

    public func decode(_ dateString: String) throws -> Date {
        guard let date = Date.laughTrackISO8601(dateString) else {
            throw DecodingError.dataCorrupted(
                .init(codingPath: [], debugDescription: "Expected ISO 8601 date string, got: \(dateString)")
            )
        }
        return date
    }
}

public extension Date {
    /// Parses a LaughTrack API ISO-8601 timestamp, accepting fractional or
    /// whole seconds. Backed by cached formatters — `ISO8601DateFormatter`
    /// options are set-at-init only, so one instance per variant is reused.
    static func laughTrackISO8601(_ dateString: String) -> Date? {
        LaughTrackISO8601Formatters.shared.date(from: dateString)
    }
}

final class LaughTrackISO8601Formatters: @unchecked Sendable {
    static let shared = LaughTrackISO8601Formatters()

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

    private init() {}

    func date(from dateString: String) -> Date? {
        lock.lock()
        defer { lock.unlock() }
        return withFractional.date(from: dateString) ?? withoutFractional.date(from: dateString)
    }

    func string(from date: Date) -> String {
        lock.lock()
        defer { lock.unlock() }
        return withFractional.string(from: date)
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
