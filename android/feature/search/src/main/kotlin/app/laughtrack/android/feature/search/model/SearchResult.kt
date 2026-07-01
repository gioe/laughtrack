package app.laughtrack.android.feature.search.model

import app.laughtrack.android.core.navigation.AppRoute

/**
 * A normalized search row, so the list UI renders all pivots uniformly and a tap
 * navigates via the typed [route] (consumed by NavController.openEntity).
 */
data class SearchResult(
    val title: String,
    val subtitle: String?,
    val metadata: List<String> = emptyList(),
    val imageUrl: String?,
    val route: AppRoute,
    val showDate: String? = null,
    val showTimezone: String? = null,
    val showRoom: String? = null,
    val showPriceLabel: String? = null,
    val isSoldOut: Boolean = false,
) {
    val artworkUrl: String?
        get() = imageUrl?.trim()?.takeIf { it.isNotEmpty() }

    val hasArtwork: Boolean
        get() = artworkUrl != null

    val displayMetadata: List<String>
        get() = listOfNotNull(subtitle?.takeIf { it.isNotBlank() }) + metadata.filter { it.isNotBlank() }
}

fun searchResultSummary(
    loaded: Int,
    total: Int,
): String {
    val noun = if (loaded == 1) "result" else "results"
    return if (total > loaded) {
        "Showing $loaded of $total results"
    } else {
        "Showing $loaded $noun"
    }
}

/**
 * Per-pivot query inputs. [zip]/[distance]/[from]/[to] only apply to the
 * geo-scoped Shows pivot; [text] filters comedians/clubs (and the club name for
 * shows); [sort] is the server sort key. [from]/[to] are inclusive YYYY-MM-DD
 * bounds used by the Home date-window shortcuts (Tonight / This Week). Changing
 * any field resets pagination and re-queries.
 */
data class SearchQuery(
    val text: String = "",
    val sort: String? = null,
    val zip: String? = null,
    val distance: Int? = null,
    val from: String? = null,
    val to: String? = null,
    // Selected comedian home-city `city|state` token; null = all home cities.
    val homeCity: String? = null,
)
