package app.laughtrack.android.feature.search.model

/**
 * The four Search pivots, mirroring iOS SearchRootView. Shows is geo-scoped (zip +
 * distance); Comedians/Clubs/Podcasts are nationwide text/filter searches.
 */
enum class SearchPivot(
    val label: String,
    val isGeoScoped: Boolean,
    val isAvailable: Boolean = true,
    /**
     * Whether the server search endpoint accepts a `filters` (tag) param. Shows,
     * Comedians, and Clubs do; the podcasts search endpoint does not, so the tag
     * filter sheet is suppressed for Podcasts even though the response echoes
     * facets.
     */
    val supportsTagFilters: Boolean = true,
) {
    SHOWS("Shows", isGeoScoped = true),
    COMEDIANS("Comedians", isGeoScoped = false),
    CLUBS("Clubs", isGeoScoped = false),
    PODCASTS("Podcasts", isGeoScoped = false, supportsTagFilters = false),
}
