package app.laughtrack.android.feature.detail.util

import java.net.URLEncoder
import java.time.Duration
import java.time.OffsetDateTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.format.FormatStyle
import java.util.Locale

/**
 * Pure formatting + URL helpers for the detail screens. Kept free of Android/Compose
 * types so they unit-test on the JVM (mirrors the iOS detail presentation helpers).
 */

/** The surface tag sent to `/tickets/out`; must be one of the contract's SOURCE_SURFACES. */
const val TICKET_SOURCE_SURFACE: String = "show_detail"

/**
 * Builds the LaughTrack outbound ticket link. Opening it logs a ticket-click event
 * server-side and 302-redirects (with affiliate routing) to [destinationUrl] —
 * the same `/api/v1/tickets/out` mechanism the web client uses. Returns null when
 * there is no destination to route to.
 */
fun buildTicketOutboundUrl(
    apiBaseUrl: String,
    showId: Int,
    clubId: Int,
    destinationUrl: String?,
): String? {
    val destination = destinationUrl?.trim().orEmpty()
    if (destination.isEmpty()) return null
    val base = apiBaseUrl.trimEnd('/')
    val params = listOf(
        "showId" to showId.toString(),
        "clubId" to clubId.toString(),
        "surface" to TICKET_SOURCE_SURFACE,
        "url" to destination,
    ).joinToString("&") { (key, value) ->
        "$key=${URLEncoder.encode(value, "UTF-8")}"
    }
    return "$base/tickets/out?$params"
}

/**
 * Parses an ISO-8601 timestamp (with or without an offset) from the API into an
 * absolute instant on the system zone, or null if it cannot be parsed.
 */
fun parseShowDateTime(raw: String): ZonedDateTime? {
    val trimmed = raw.trim()
    if (trimmed.isEmpty()) return null
    return runCatching { OffsetDateTime.parse(trimmed).toZonedDateTime() }
        .recoverCatching { ZonedDateTime.parse(trimmed) }
        .recoverCatching {
            java.time.LocalDateTime.parse(trimmed).atZone(java.time.ZoneId.systemDefault())
        }
        .getOrNull()
}

/** Human-readable date/time for a show, e.g. "Fri, Jun 27, 8:00 PM". Falls back to the raw string. */
fun formatShowDateTime(raw: String): String {
    val parsed = parseShowDateTime(raw) ?: return raw
    val formatter = DateTimeFormatter
        .ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
        .withLocale(Locale.getDefault())
    return parsed.format(formatter)
}

/**
 * A short countdown label from [now] to the show at [raw], e.g. "In 3 days",
 * "In 5 hours", "Starting soon", or "Past show". Null when the date can't be parsed.
 */
fun formatCountdown(raw: String, now: ZonedDateTime): String? {
    val target = parseShowDateTime(raw) ?: return null
    val until = Duration.between(now, target)
    val days = until.toDays()
    val hours = until.toHours()
    val minutes = until.toMinutes()
    return when {
        until.isNegative -> "Past show"
        days >= 1 -> "In $days ${plural(days, "day")}"
        hours >= 1 -> "In $hours ${plural(hours, "hour")}"
        minutes >= 1 -> "In $minutes ${plural(minutes, "minute")}"
        else -> "Starting soon"
    }
}

/** Formats an episode duration in seconds as "1h 12m" / "47m" / "0m". */
fun formatEpisodeDuration(seconds: Int?): String? {
    if (seconds == null || seconds <= 0) return null
    val totalMinutes = seconds / 60
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours}h ${minutes}m" else "${minutes}m"
}

/** Formats a release date like "2026-06-14" or an ISO timestamp as a medium date. */
fun formatReleaseDate(raw: String?): String? {
    val trimmed = raw?.trim().orEmpty()
    if (trimmed.isEmpty()) return null
    val formatter = DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(Locale.getDefault())
    return runCatching { java.time.LocalDate.parse(trimmed).format(formatter) }
        .recoverCatching { parseShowDateTime(trimmed)?.format(formatter) ?: throw DateTimeParseException("", trimmed, 0) }
        .getOrDefault(trimmed)
}

private fun plural(count: Long, unit: String): String = if (count == 1L) unit else "${unit}s"
