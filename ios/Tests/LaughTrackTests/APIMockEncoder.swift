import Foundation

/// Shared `JSONEncoder` factory for mock `ClientTransport` responses that encode
/// generated API types containing `Date` fields.
///
/// The production API client decodes responses with
/// `LaughTrackFlexibleISO8601DateTranscoder`, which expects ISO-8601 strings.
/// `JSONEncoder`'s default `dateEncodingStrategy` is `.deferredToDate` (numeric
/// seconds-since-2001), so a mock transport that omits `.iso8601` produces a
/// payload the production decoder cannot parse — silently breaking otherwise
/// valid response fixtures (TASK-1881).
///
/// Use `APIMockEncoder.make()` from any mock transport that encodes generated
/// API response types so the date strategy stays aligned in one place.
enum APIMockEncoder {
    static func make() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}
