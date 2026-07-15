package app.laughtrack.android.feature.detail.util

import app.laughtrack.android.core.network.generated.model.Ticket
import java.math.BigDecimal
import java.math.RoundingMode
import java.net.URLEncoder
import java.time.Duration
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.format.FormatStyle
import java.util.Locale

/*
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
    val params =
        listOf(
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
 * absolute instant in [timezone], or in the timestamp/system zone when no valid
 * venue timezone is supplied. Returns null if [raw] cannot be parsed.
 */
fun parseShowDateTime(
    raw: String,
    timezone: String? = null,
): ZonedDateTime? {
    val trimmed = raw.trim()
    if (trimmed.isEmpty()) return null
    val venueZone = timezone?.let { runCatching { ZoneId.of(it) }.getOrNull() }
    return runCatching {
        val parsed = OffsetDateTime.parse(trimmed)
        venueZone?.let(parsed::atZoneSameInstant) ?: parsed.toZonedDateTime()
    }
        .recoverCatching {
            val parsed = ZonedDateTime.parse(trimmed)
            venueZone?.let(parsed::withZoneSameInstant) ?: parsed
        }
        .recoverCatching {
            java.time.LocalDateTime.parse(trimmed).atZone(venueZone ?: ZoneId.systemDefault())
        }
        .getOrNull()
}

/** Human-readable date/time for a show, e.g. "Fri, Jun 27, 8:00 PM". Falls back to the raw string. */
fun formatShowDateTime(
    raw: String,
    timezone: String? = null,
): String {
    val parsed = parseShowDateTime(raw, timezone) ?: return raw
    val formatter =
        DateTimeFormatter
            .ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
            .withLocale(Locale.getDefault())
    return parsed.format(formatter)
}

/**
 * A short countdown label from [now] to the show at [raw], e.g. "In 3 days",
 * "In 5 hours", "Starting soon", or "Past show". Null when the date can't be parsed.
 */
fun formatCountdown(
    raw: String,
    now: ZonedDateTime,
): String? {
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

/**
 * Label for a ticket-stub footer: "Sold out", "Free", or the cheapest available
 * price ("$25.00"). Null when the show has no priced, available tickets.
 */
fun formatTicketPriceLabel(
    tickets: List<Ticket>?,
    soldOut: Boolean?,
): String? {
    if (soldOut == true) return "Sold out"
    val available = tickets.orEmpty().filter { it.soldOut != true }
    if (available.isEmpty() && !tickets.isNullOrEmpty()) return "Sold out"
    val price = available.mapNotNull { it.price }.minOrNull() ?: return null
    return if (price.compareTo(BigDecimal.ZERO) == 0) {
        "Free"
    } else {
        "$" + price.setScale(2, RoundingMode.HALF_UP).toPlainString()
    }
}

/**
 * Title/subtitle pair for a show list row: the title prefers the show name and
 * falls back to the club name; the subtitle drops the club name when it would
 * repeat the title, joining what remains with the club city.
 */
fun showRowTitleSubtitle(
    name: String?,
    clubName: String?,
    clubCity: String?,
): Pair<String, String?> {
    val title = name ?: clubName ?: "Show"
    val subtitle =
        listOfNotNull(
            clubName?.takeUnless { it.equals(title, ignoreCase = true) },
            clubCity,
        ).joinToString(" · ").ifBlank { null }
    return title to subtitle
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
        .recoverCatching {
            parseShowDateTime(trimmed)?.format(formatter)
                ?: throw DateTimeParseException("", trimmed, 0)
        }
        .getOrDefault(trimmed)
}

private fun plural(
    count: Long,
    unit: String,
): String = if (count == 1L) unit else "${unit}s"

/** Trims whitespace and treats blank strings as absent. */
private fun blankToNull(value: String?): String? = value?.trim()?.takeIf { it.isNotEmpty() }

/**
 * "City, Region" label for a comedian's derived home location, where region
 * prefers state and falls back to country. Returns null when there is no city
 * to anchor the label so the row can be omitted.
 */
fun formatHomeCity(
    city: String?,
    state: String?,
    country: String?,
): String? {
    val resolvedCity = blankToNull(city) ?: return null
    val region = blankToNull(state) ?: blankToNull(country)
    return if (region != null) "$resolvedCity, $region" else resolvedCity
}

/** The displayable home club name, or null when blank/absent. */
fun formatHomeClubName(clubName: String?): String? = blankToNull(clubName)
