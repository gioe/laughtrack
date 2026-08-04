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
    val favoriteTarget: SearchFavoriteTarget? = null,
    val isFavorite: Boolean = false,
) {
    val artworkUrl: String?
        get() = imageUrl?.trim()?.takeIf { it.isNotEmpty() }

    val hasArtwork: Boolean
        get() = artworkUrl != null

    val displayMetadata: List<String>
        get() = listOfNotNull(subtitle?.takeIf { it.isNotBlank() }) + metadata.filter { it.isNotBlank() }
}

/** Typed API identity used by the favorite control on parity search rows. */
sealed interface SearchFavoriteTarget {
    data class Comedian(val uuid: String) : SearchFavoriteTarget

    data class Podcast(val id: Int) : SearchFavoriteTarget
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
 * Per-pivot query inputs. [zip]/[distance] apply to geo-scoped pivots; [from]/[to]
 * only apply to Shows. [text] is retained for the Comedians, Clubs, and Podcasts
 * pivots; Shows instead use the explicit optional [comedian] and [club]
 * constraints. [sort] is the server sort key and [maxPrice] is the greatest
 * acceptable public ticket price for Shows.
 * [from]/[to] are inclusive YYYY-MM-DD bounds set by the date-range picker.
 * [filters] holds selected tag slugs (joined into the `filters` query param);
 * [homeCity] is the `city|state` token for the comedians home-city filter.
 * Changing any field resets pagination and re-queries.
 */
data class SearchQuery(
    val text: String = "",
    val comedian: String = "",
    val club: String = "",
    val sort: String? = null,
    val zip: String? = null,
    val distance: Int? = null,
    val from: String? = null,
    val to: String? = null,
    val filters: Set<String> = emptySet(),
    val maxPrice: Int? = null,
    val homeCity: String? = null,
)

/**
 * Complete, transport-independent state needed to seed the Shows explorer.
 * TASK-3884 can carry this value across navigation without reconstructing
 * individual filters from presentation labels.
 */
data class ShowSearchSeed(
    val comedian: String = "",
    val club: String = "",
    val zip: String? = null,
    val locationLabel: String? = null,
    val distance: Int = DEFAULT_DISTANCE_MILES,
    val from: String? = null,
    val to: String? = null,
    val filters: Set<String> = emptySet(),
    val maxPrice: Int? = null,
    val resultsPresentation: ShowResultsPresentation = ShowResultsPresentation.AGENDA,
)

/** Typed identity for a removable show constraint. */
sealed interface ShowActiveConstraintKind {
    data object Location : ShowActiveConstraintKind

    data object Date : ShowActiveConstraintKind

    data class Filter(val slug: String) : ShowActiveConstraintKind

    data object MaximumPrice : ShowActiveConstraintKind

    data object Comedian : ShowActiveConstraintKind

    data object Club : ShowActiveConstraintKind
}

data class ShowActiveConstraint(
    val kind: ShowActiveConstraintKind,
    val label: String,
)
