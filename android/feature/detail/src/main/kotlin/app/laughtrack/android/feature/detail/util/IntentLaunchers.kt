package app.laughtrack.android.feature.detail.util

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.CalendarContract

/*
 * Thin wrappers over the Android Intents the detail screens fire for outbound
 * actions: opening links/maps/dialers, sharing, and inserting a calendar event.
 * None require a runtime permission — calendar insertion uses the system
 * `ACTION_INSERT` editor rather than writing to the provider directly.
 */

/** Opens [url] in the user's browser (or the app that handles it). No-ops on a blank/invalid URL. */
fun Context.openUrl(url: String?) {
    val target = url?.trim().orEmpty()
    if (target.isEmpty()) return
    safeStart(Intent(Intent.ACTION_VIEW, Uri.parse(target)))
}

/** Shares [url] (with an optional [title]) via the system share sheet. */
fun Context.shareLink(
    url: String?,
    title: String?,
) {
    val target = url?.trim().orEmpty()
    if (target.isEmpty()) return
    val text = if (title.isNullOrBlank()) target else "$title\n$target"
    val intent =
        Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
            title?.let { putExtra(Intent.EXTRA_SUBJECT, it) }
        }
    safeStart(Intent.createChooser(intent, title ?: "Share"))
}

/** Opens the dialer pre-filled with [number]. */
fun Context.dialPhone(number: String?) {
    val target = number?.trim().orEmpty()
    if (target.isEmpty()) return
    safeStart(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$target")))
}

/** Opens a maps app at [label]'s address query. */
fun Context.openMap(query: String?) {
    val target = query?.trim().orEmpty()
    if (target.isEmpty()) return
    val geo = Uri.parse("geo:0,0?q=${Uri.encode(target)}")
    safeStart(Intent(Intent.ACTION_VIEW, geo))
}

/**
 * Launches the system calendar's event editor pre-filled with the show. [startMillis]
 * and [endMillis] are epoch millis; a null end defaults to two hours after start
 * (matching the iOS EventKit export).
 */
fun Context.addEventToCalendar(
    title: String,
    startMillis: Long,
    endMillis: Long?,
    location: String?,
    description: String?,
) {
    val intent =
        Intent(Intent.ACTION_INSERT).apply {
            data = CalendarContract.Events.CONTENT_URI
            putExtra(CalendarContract.Events.TITLE, title)
            putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMillis)
            putExtra(CalendarContract.EXTRA_EVENT_END_TIME, endMillis ?: (startMillis + TWO_HOURS_MILLIS))
            location?.takeIf { it.isNotBlank() }?.let { putExtra(CalendarContract.Events.EVENT_LOCATION, it) }
            description?.takeIf { it.isNotBlank() }?.let { putExtra(CalendarContract.Events.DESCRIPTION, it) }
        }
    safeStart(intent)
}

private fun Context.safeStart(intent: Intent) {
    // NEW_TASK lets this start from a non-Activity context; harmless from an Activity.
    val launchable = intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { startActivity(launchable) }
        .onFailure { error -> if (error !is ActivityNotFoundException) throw error }
}

private const val TWO_HOURS_MILLIS = 2L * 60L * 60L * 1000L
