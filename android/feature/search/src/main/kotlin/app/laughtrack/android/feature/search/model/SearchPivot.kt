package app.laughtrack.android.feature.search.model

/**
 * The four Search pivots, mirroring iOS SearchRootView. Shows is geo-scoped (zip +
 * distance); Comedians/Clubs are nationwide text/filter searches; Podcasts is
 * disabled until /podcasts/search is added to the OpenAPI spec (TASK-3273) — the
 * generated client has no podcast-search method.
 */
enum class SearchPivot(
    val label: String,
    val isGeoScoped: Boolean,
    val isAvailable: Boolean = true,
) {
    SHOWS("Shows", isGeoScoped = true),
    COMEDIANS("Comedians", isGeoScoped = false),
    CLUBS("Clubs", isGeoScoped = false),
    PODCASTS("Podcasts", isGeoScoped = false, isAvailable = false),
}
