package app.laughtrack.android.core.navigation

/**
 * The three bottom-navigation tabs, each mapped to its root route. Order is the
 * left-to-right tab-bar order: Discover, Search, Library.
 */
enum class AppTab(
    val rootRoute: AppRoute,
    val label: String,
    val ownsEntityPivots: Boolean = false,
) {
    DISCOVER(AppRoute.Discover, "Discover"),
    SEARCH(AppRoute.Search, "Search", ownsEntityPivots = true),
    FAVORITES(AppRoute.Favorites, "Library"),
}
