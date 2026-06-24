package app.laughtrack.android.feature.search.model

import app.laughtrack.android.core.navigation.AppRoute

/**
 * A normalized search row, so the list UI renders all pivots uniformly and a tap
 * navigates via the typed [route] (consumed by NavController.openEntity).
 */
data class SearchResult(
    val title: String,
    val subtitle: String?,
    val imageUrl: String?,
    val route: AppRoute,
)

/**
 * Per-pivot query inputs. [zip]/[distance] only apply to the geo-scoped Shows
 * pivot; [text] filters comedians/clubs (and the club name for shows); [sort] is
 * the server sort key. Changing any field resets pagination and re-queries.
 */
data class SearchQuery(
    val text: String = "",
    val sort: String? = null,
    val zip: String? = null,
    val distance: Int? = null,
)
