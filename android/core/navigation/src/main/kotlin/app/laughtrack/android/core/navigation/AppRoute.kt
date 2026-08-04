package app.laughtrack.android.core.navigation

import kotlinx.serialization.Serializable

/**
 * Typed navigation destinations, mirroring the iOS AppRoute enum.
 *
 * The three tab roots are the top-level graphs; the `*Detail` routes push onto
 * the active tab's back stack; `Profile` and `NotificationCenter` are reached
 * from the profile menu (not tabs). Every concrete route is `@Serializable` so
 * the Navigation-Compose type-safe NavHost API can use them directly.
 */
sealed interface AppRoute {
    @Serializable
    data object Discover : AppRoute

    @Serializable
    data object Search : AppRoute

    // showIds scope the Favorites "touring" section to a notification's shows;
    // empty (the default) = the full Favorites tab.
    @Serializable
    data class Favorites(val showIds: List<Int> = emptyList()) : AppRoute

    @Serializable
    data object ComedianOnboarding : AppRoute

    @Serializable
    data class ShowDetail(val id: Int) : AppRoute

    @Serializable
    data class ComedianDetail(
        val id: Int,
        val showIds: List<Int> = emptyList(),
    ) : AppRoute

    @Serializable
    data class ClubDetail(val id: Int) : AppRoute

    @Serializable
    data class PodcastDetail(val id: Int) : AppRoute

    @Serializable
    data class PodcastEpisodeDetail(val id: Int) : AppRoute

    @Serializable
    data object NowPlaying : AppRoute

    @Serializable
    data object Profile : AppRoute

    @Serializable
    data object NotificationCenter : AppRoute
}

/** Search section selected by a one-shot cross-feature launch request. */
enum class SearchDestination {
    SHOWS,
    COMEDIANS,
    CLUBS,
    PODCASTS,
}

/**
 * Transport-neutral constraints carried from suggestion surfaces into Search.
 *
 * This deliberately is not part of [AppRoute.Search]: Search remains a stable
 * tab root, while the app shell consumes each request exactly once. That keeps
 * returning from details from reapplying the original filters over user edits.
 */
data class SearchLaunchRequest(
    val destination: SearchDestination,
    val comedian: String = "",
    val club: String = "",
    val zip: String? = null,
    val locationLabel: String? = null,
    val distanceMiles: Int? = null,
    val from: String? = null,
    val to: String? = null,
    val filters: Set<String> = emptySet(),
    val maxPrice: Int? = null,
)
