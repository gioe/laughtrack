import Foundation
import LaughTrackAPIClient

/// Shared `JSONEncoder` factory for mock `ClientTransport` responses that encode
/// generated API types containing `Date` fields.
///
/// The production API client decodes responses with
/// `LaughTrackFlexibleISO8601DateTranscoder` (see `LaughTrackAPIConfiguration`),
/// which accepts ISO-8601 with or without fractional seconds. `JSONEncoder`'s
/// default `dateEncodingStrategy` is `.deferredToDate` (numeric
/// seconds-since-2001), so a mock transport that omits a string-based strategy
/// produces a payload the production decoder cannot parse — silently breaking
/// otherwise valid response fixtures (TASK-1881). Using the same transcoder the
/// production decoder is configured with also guarantees encoder/decoder symmetry
/// (TASK-2445), so a fixture's Date round-trips losslessly.
///
/// Use `APIMockEncoder.make()` from any mock transport that encodes generated
/// API response types so the date strategy stays aligned in one place.
enum APIMockEncoder {
    static func make() -> JSONEncoder {
        let encoder = JSONEncoder()
        let transcoder = LaughTrackFlexibleISO8601DateTranscoder()
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(try transcoder.encode(date))
        }
        return encoder
    }
}
