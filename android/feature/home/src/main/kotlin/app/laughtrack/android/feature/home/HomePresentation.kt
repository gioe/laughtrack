package app.laughtrack.android.feature.home

import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import java.math.BigDecimal
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

internal fun showHeadliner(show: Show): ComedianLineup? =
    show.lineup
        ?.map(::effectiveComedian)
        ?.filter { it.imageUrl.isNotBlank() }
        ?.maxByOrNull { it.showCount ?: 0 }

internal fun showSupportingLineup(
    show: Show,
    excluding: ComedianLineup?,
): List<ComedianLineup> =
    show.lineup
        ?.map(::effectiveComedian)
        ?.filter { excluding == null || it.id != excluding.id }
        ?.sortedByDescending { it.showCount ?: 0 }
        ?.take(3)
        .orEmpty()

private fun effectiveComedian(comedian: ComedianLineup): ComedianLineup = comedian.parentComedian ?: comedian

internal fun heroArtworkComedian(show: Show): ComedianLineup? {
    val showImage = show.imageUrl.trim()
    val lineup = show.lineup.orEmpty().map(::effectiveComedian)
    return lineup.firstOrNull { showImage.isNotEmpty() && it.imageUrl.trim() == showImage }
        ?: lineup.filter { it.imageUrl.isNotBlank() }.maxByOrNull { it.showCount ?: 0 }
}

internal fun heroArtworkUrl(show: Show): String? =
    heroArtworkComedian(show)?.imageUrl?.takeIf { it.isNotBlank() }
        ?: show.imageUrl.takeIf { it.isNotBlank() }

internal fun heroArtworkCaption(show: Show): String =
    heroArtworkComedian(show)?.name?.takeIf { it.isNotBlank() } ?: showListTitle(show)

internal fun showTicketBadges(show: Show): List<String> =
    buildList {
        if (isOpenMic(show)) add("Open mic")
        if (show.soldOut == true) add("Sold out")
    }

private fun isOpenMic(show: Show): Boolean {
    val title = show.name.orEmpty()
    val tags = show.tags.orEmpty()
    return title.contains("open mic", ignoreCase = true) ||
        tags.any { tag ->
            tag.slug.contains("open-mic", ignoreCase = true) ||
                tag.name.contains("open mic", ignoreCase = true)
        }
}

internal fun showListTitle(show: Show): String {
    val title = show.name?.trim().orEmpty()
    if (title.isNotEmpty()) return title
    return show.clubName?.let { "Comedy show at $it" } ?: "Comedy show"
}

internal fun roomLabel(show: Show): String? {
    val room = show.room?.trim().orEmpty()
    if (room.isEmpty()) return null
    val club = show.clubName?.trim().orEmpty()
    return room.takeUnless { it.equals(club, ignoreCase = true) }
}

internal fun formatPrice(prices: List<BigDecimal>?): String? {
    val price = prices?.filter { it >= BigDecimal.ZERO }?.minOrNull() ?: return null
    return "$${price.stripTrailingZeros().toPlainString()}"
}

internal fun formatShowTime(show: Show): String? {
    val time =
        ticketStubDateParts(isoDateTime = show.date, timezone = show.timezone)
            .time
            .takeIf { it.isNotBlank() } ?: return null
    val zone =
        runCatching {
            val zoneId = show.timezone?.let(ZoneId::of) ?: return@runCatching null
            OffsetDateTime.parse(show.date)
                .atZoneSameInstant(zoneId)
                .format(DateTimeFormatter.ofPattern("z", Locale.US))
        }.getOrNull()
    return listOfNotNull(time, zone).joinToString(" ")
}
