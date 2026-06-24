package app.laughtrack.android.core.navigation

/**
 * The three bottom-navigation tabs, each mapped to its root route. Order is the
 * left-to-right tab-bar order: Discover, Search, Favorites (mirrors iOS AppTab).
 */
enum class AppTab(val rootRoute: AppRoute, val label: String) {
    DISCOVER(AppRoute.Discover, "Discover"),
    SEARCH(AppRoute.Search, "Search"),
    FAVORITES(AppRoute.Favorites, "Favorites"),
}
