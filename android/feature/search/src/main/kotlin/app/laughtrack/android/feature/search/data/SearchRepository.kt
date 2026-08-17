package app.laughtrack.android.feature.search.data

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Filter
import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.feature.search.model.SearchFavoriteTarget
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchQuery
import app.laughtrack.android.feature.search.model.SearchResult
import java.math.BigDecimal
import javax.inject.Inject

/**
 * One page of normalized results plus the server's total (drives hasMore) and the
 * available tag facets ([filters]) / comedian home-city facets ([homeCityFilters])
 * returned alongside the page — these populate the tag and home-city filter sheets.
 */
data class SearchPage(
    val results: List<SearchResult>,
    val total: Int,
    val filters: List<Filter> = emptyList(),
    val homeCityFilters: List<HomeCityFilter> = emptyList(),
)

/** Joins selected tag slugs into the comma-separated `filters` query param (null when empty). */
private fun Set<String>.toFiltersParam(): String? = takeIf { it.isNotEmpty() }?.sorted()?.joinToString(",")

/**
 * Wraps the generated search APIs and normalizes each entity into [SearchResult].
 * Shows and Clubs are geo-scoped (zip/distance); Comedians and Podcasts are nationwide.
 * The X-Timezone header is set globally by the network interceptor.
 */
class SearchRepository
    @Inject
    constructor(
        private val showsApi: ShowsApi,
        private val comediansApi: ComediansApi,
        private val clubsApi: ClubsApi,
        private val podcastsApi: PodcastsApi,
    ) {
        suspend fun search(
            pivot: SearchPivot,
            query: SearchQuery,
            page: Int,
            size: Int = PAGE_SIZE,
        ): SearchPage =
            when (pivot) {
                SearchPivot.SHOWS -> showsPage(query, page, size)
                SearchPivot.COMEDIANS -> comediansPage(query, page, size)
                SearchPivot.CLUBS -> clubsPage(query, page, size)
                SearchPivot.PODCASTS -> podcastsPage(query, page, size)
            }

        private suspend fun showsPage(
            query: SearchQuery,
            page: Int,
            size: Int,
        ): SearchPage {
            val response =
                showsApi.searchShows(
                    zip = query.zip,
                    from = query.from,
                    to = query.to,
                    distance = query.distance,
                    sort = query.sort,
                    comedian = query.comedian.ifBlank { null },
                    club = query.club.ifBlank { null },
                    filters = query.filters.toFiltersParam(),
                    maxPrice = query.maxPrice?.toBigDecimal(),
                    page = page,
                    size = size,
                )
            val body = response.body() ?: error("Shows search failed (HTTP ${response.code()})")
            return SearchPage(
                filters = body.filters,
                results =
                    body.data.map { show ->
                        SearchResult(
                            title = show.name ?: "Show",
                            subtitle = show.clubName,
                            metadata =
                                listOfNotNull(
                                    show.date,
                                    listOfNotNull(show.clubCity, show.clubState).joinToString(", ").ifBlank { null },
                                    show.room,
                                ),
                            imageUrl = showSearchArtworkUrl(show),
                            route = AppRoute.ShowDetail(show.id),
                            showDate = show.date,
                            showTimezone = show.timezone,
                            showRoom = show.room,
                            showPriceLabel =
                                formatSearchPrice(
                                    show.tickets
                                        ?.filter { it.soldOut != true }
                                        ?.mapNotNull { it.price },
                                ),
                            isSoldOut = show.soldOut == true,
                        )
                    },
                total = body.total,
            )
        }

        private suspend fun comediansPage(
            query: SearchQuery,
            page: Int,
            size: Int,
        ): SearchPage {
            val response =
                comediansApi.searchComedians(
                    comedian = query.text.ifBlank { null },
                    sort = query.sort,
                    filters = query.filters.toFiltersParam(),
                    homeCity = query.homeCity,
                    page = page,
                    size = size,
                )
            val body = response.body() ?: error("Comedians search failed (HTTP ${response.code()})")
            return SearchPage(
                filters = body.filters,
                homeCityFilters = body.homeCityFilters,
                results =
                    body.data.map { comedian ->
                        SearchResult(
                            title = comedian.name,
                            subtitle = "${comedian.showCount} shows",
                            metadata =
                                listOfNotNull(
                                    comedian.socialData.instagramAccount?.let { "Instagram: @$it" },
                                    comedian.socialData.youtubeAccount?.let { "YouTube" },
                                ),
                            imageUrl = comedian.imageUrl,
                            route = AppRoute.ComedianDetail(comedian.id),
                            favoriteTarget = SearchFavoriteTarget.Comedian(comedian.uuid),
                            isFavorite = comedian.isFavorite == true,
                        )
                    },
                total = body.total,
            )
        }

        private suspend fun clubsPage(
            query: SearchQuery,
            page: Int,
            size: Int,
        ): SearchPage {
            val response =
                clubsApi.searchClubs(
                    club = query.text.ifBlank { null },
                    zip = query.zip,
                    distance = query.distance,
                    sort = query.sort,
                    filters = query.filters.toFiltersParam(),
                    page = page,
                    size = size,
                )
            val body = response.body() ?: error("Clubs search failed (HTTP ${response.code()})")
            return SearchPage(
                filters = body.filters,
                results =
                    body.data.mapNotNull { club ->
                        val id = club.id ?: return@mapNotNull null
                        SearchResult(
                            title = club.name ?: "Club",
                            subtitle = listOfNotNull(club.city, club.state).joinToString(", ").ifBlank { null },
                            metadata =
                                listOfNotNull(
                                    club.showCount?.let { "$it shows" },
                                    club.activeComedianCount?.let { "$it active comedians" },
                                    club.address,
                                ),
                            imageUrl = club.imageUrl,
                            route = AppRoute.ClubDetail(id),
                        )
                    },
                total = body.total,
            )
        }

        private suspend fun podcastsPage(
            query: SearchQuery,
            page: Int,
            size: Int,
        ): SearchPage {
            val response =
                podcastsApi.searchPodcasts(
                    q = query.text.ifBlank { null },
                    sort = query.sort,
                    page = page,
                    size = size,
                )
            val body = response.body() ?: error("Podcasts search failed (HTTP ${response.code()})")
            return SearchPage(
                filters = body.filters,
                results =
                    body.data.map { podcast ->
                        SearchResult(
                            title = podcast.title,
                            subtitle = podcast.authorName,
                            metadata =
                                listOfNotNull(
                                    "${podcast.episodeCount} episodes",
                                    podcast.hosts.takeIf { it.isNotEmpty() }?.joinToString(", ") { it.name },
                                ),
                            imageUrl = podcast.imageUrl,
                            route = AppRoute.PodcastDetail(podcast.id),
                            favoriteTarget = SearchFavoriteTarget.Podcast(podcast.id),
                            isFavorite = podcast.isFavorite == true,
                        )
                    },
                total = body.total,
            )
        }

        /**
         * Fetches per-day counts for a calendar month. The density endpoint can
         * mirror location and explicit entity constraints, but not show-format,
         * Free, or maximum-price constraints.
         */
        suspend fun showDensity(
            query: SearchQuery,
            from: String,
            to: String,
        ): Map<String, Int> {
            // Density accepts either comedian or club, not both. When the result
            // query combines them, keep the calendar useful with broader
            // location-only dots instead of issuing a guaranteed HTTP 400.
            val hasComedian = query.comedian.isNotBlank()
            val hasClub = query.club.isNotBlank()
            val response =
                showsApi.getShowsDensity(
                    zip = query.zip,
                    from = from,
                    to = to,
                    distance = query.distance,
                    comedian = query.comedian.takeIf { hasComedian && !hasClub },
                    club = query.club.takeIf { hasClub && !hasComedian },
                )
            return response.body() ?: error("Show density failed (HTTP ${response.code()})")
        }

        private companion object {
            const val PAGE_SIZE = 20
        }
    }

internal fun formatSearchPrice(prices: List<BigDecimal>?): String? {
    val lowest = prices?.filter { it >= BigDecimal.ZERO }?.minOrNull() ?: return null
    if (lowest.compareTo(BigDecimal.ZERO) == 0) return "Free"

    val normalized = lowest.stripTrailingZeros()
    return "$${normalized.toPlainString()}"
}

internal fun showSearchArtworkUrl(show: Show): String? {
    val headliner =
        show.lineup
            ?.map(::effectiveComedian)
            ?.filter { it.imageUrl.isAbsoluteHttpUrl() }
            ?.maxByOrNull { it.showCount ?: 0 }

    return headliner?.imageUrl ?: show.imageUrl.takeIf { it.isAbsoluteHttpUrl() }
}

private fun effectiveComedian(comedian: ComedianLineup): ComedianLineup = comedian.parentComedian ?: comedian

private fun String?.isAbsoluteHttpUrl(): Boolean {
    val value = this?.trim().orEmpty()
    return value.startsWith("https://", ignoreCase = true) || value.startsWith("http://", ignoreCase = true)
}
