package app.laughtrack.android.core.network.time

import java.time.Instant
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException

/**
 * Flexible ISO-8601 decoder for the date-time strings the `/api/v1` backend emits.
 *
 * The contract is inconsistent on the wire: some endpoints emit fractional
 * seconds (`2024-06-21T15:30:45.123Z`), others whole seconds
 * (`2024-06-21T15:30:45Z`), and some carry a numeric UTC offset instead of `Z`.
 * This mirrors the iOS `LaughTrackFlexibleISO8601DateTranscoder` so both clients
 * decode the same wire formats identically.
 *
 * The generated models carry date-times as `kotlin.String` (dateLibrary=string);
 * call sites convert through here rather than parsing inline.
 */
object LaughTrackInstant {
    /**
     * Parse an ISO-8601 timestamp, accepting fractional **or** whole seconds and
     * either a `Z` suffix or a numeric UTC offset. Throws [DateTimeParseException]
     * on an unparseable value.
     */
    fun parse(raw: String): Instant =
        try {
            // Instant.parse handles the `Z` forms with or without fractional seconds.
            Instant.parse(raw)
        } catch (_: DateTimeParseException) {
            // Fall back to offset forms (e.g. `...+00:00`, `...-07:00`).
            OffsetDateTime.parse(raw).toInstant()
        }

    /** Lenient variant: returns `null` for null/blank/unparseable input instead of throwing. */
    fun parseOrNull(raw: String?): Instant? {
        if (raw.isNullOrBlank()) return null
        return try {
            parse(raw)
        } catch (_: DateTimeParseException) {
            null
        }
    }

    /** Canonical ISO-8601 rendering (UTC, `Z` suffix) for values sent back to the API. */
    fun format(instant: Instant): String = instant.toString()
}
