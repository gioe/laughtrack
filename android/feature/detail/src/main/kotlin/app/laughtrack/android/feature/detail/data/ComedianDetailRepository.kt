package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import app.laughtrack.android.feature.detail.model.ComedianPinnedShowsPage
import app.laughtrack.android.feature.detail.model.DEFAULT_COMEDIAN_DISTANCE_MILES
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import javax.inject.Inject

/**
 * Loads Comedian detail and the data behind its three tabs. The core profile comes
 * from `GET /comedians/{id}` (which carries podcast appearances); the Shows tab
 * unions `GET /comedians/{id}/upcoming-runs` with `GET /comedians/past-shows`
 * (keyed by name, not id); the Related tab is `GET /comedians/{id}/co-bill`. The
 * three secondary calls run concurrently and degrade to empty lists on failure so
 * one slow/absent endpoint never blanks the whole screen. The primary constructor
 * takes the generated [ComediansApi] interface directly so JVM unit tests can
 * construct the repository over a fake; the Hilt path builds the service from the
 * shared configured [ApiClient].
 */
class ComedianDetailRepository(
    private val comediansApi: ComediansApi,
    private val showsApi: ShowsApi,
) {
    @Inject
    constructor(apiClient: ApiClient) : this(
        apiClient.createService(ComediansApi::class.java),
        apiClient.createService(ShowsApi::class.java),
    )

    suspend fun getComedian(
        id: Int,
        zip: String? = null,
        locationLabel: String? = null,
        distanceMiles: Int? = null,
    ): ComedianDetailUi =
        coroutineScope {
            val detailResponse = comediansApi.getComedian(id)
            val detail =
                detailResponse.body()?.data
                    ?: error("Comedian unavailable (HTTP ${detailResponse.code()})")

            val upcomingDeferred =
                async {
                    runCatchingCancellable {
                        comediansApi.getComedianUpcomingRuns(id).body()?.data
                    }.getOrNull().orEmpty()
                }
            val coBillDeferred =
                async {
                    runCatchingCancellable {
                        comediansApi.getComedianCoBill(id).body()?.data
                    }.getOrNull().orEmpty()
                }
            val pastShowsDeferred =
                async {
                    runCatchingCancellable {
                        comediansApi.getComedianPastShows(
                            detail.name,
                        ).body()?.data
                    }.getOrNull().orEmpty()
                }
            val pinnedShowsDeferred =
                async {
                    runCatchingCancellable {
                        getPinnedShows(
                            comedianName = detail.name,
                            zip = zip,
                            distanceMiles = distanceMiles,
                            page = 0,
                        )
                    }.getOrNull()
                }
            val pinnedShowsPage = pinnedShowsDeferred.await()

            ComedianDetailUi(
                detail = detail,
                upcomingRuns = upcomingDeferred.await(),
                pastShows = pastShowsDeferred.await(),
                coBill = coBillDeferred.await(),
                pinnedShows = pinnedShowsPage?.shows.orEmpty(),
                pinnedShowsTotal = pinnedShowsPage?.total ?: 0,
                currentPinnedShowsPage = pinnedShowsPage?.page ?: 0,
                activeZip = zip,
                activeLocationLabel = locationLabel,
                activeDistanceMiles = distanceMiles ?: DEFAULT_COMEDIAN_DISTANCE_MILES,
            )
        }

    suspend fun getPinnedShows(
        comedianName: String,
        zip: String?,
        distanceMiles: Int?,
        page: Int,
    ): ComedianPinnedShowsPage {
        val response =
            showsApi.searchShows(
                zip = zip,
                distance = distanceMiles,
                comedian = comedianName,
                page = page,
                size = PINNED_SHOWS_PAGE_SIZE,
            )
        val body = response.body() ?: error("Comedian shows unavailable (HTTP ${response.code()})")
        return ComedianPinnedShowsPage(
            shows = body.data,
            total = body.total,
            page = page,
        )
    }

    private companion object {
        const val PINNED_SHOWS_PAGE_SIZE = 20
    }
}
