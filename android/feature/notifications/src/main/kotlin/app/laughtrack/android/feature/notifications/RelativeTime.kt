package app.laughtrack.android.feature.notifications

import java.time.Duration
import java.time.OffsetDateTime
import java.time.ZonedDateTime

/**
 * Formats an ISO-8601 timestamp as a compact "time ago" label (e.g. "3d", "2h",
 * "5m", "now"), mirroring the iOS notification-center relative timestamps. Pure
 * (no Android types) so it unit-tests on the JVM. Returns null if unparseable.
 */
fun formatTimeAgo(
    iso: String?,
    now: ZonedDateTime,
): String? {
    val trimmed = iso?.trim().orEmpty()
    if (trimmed.isEmpty()) return null
    val sent =
        runCatching { OffsetDateTime.parse(trimmed).toZonedDateTime() }
            .recoverCatching { ZonedDateTime.parse(trimmed) }
            .getOrNull()
    return sent?.let { label(Duration.between(it, now).seconds) }
}

// seconds < MINUTE also covers future timestamps (negative elapsed) → "now".
private fun label(seconds: Long): String =
    when {
        seconds < MINUTE -> "now"
        seconds < HOUR -> "${seconds / MINUTE}m"
        seconds < DAY -> "${seconds / HOUR}h"
        seconds < WEEK -> "${seconds / DAY}d"
        else -> "${seconds / WEEK}w"
    }

private const val MINUTE = 60L
private const val HOUR = 60L * MINUTE
private const val DAY = 24L * HOUR
private const val WEEK = 7L * DAY
