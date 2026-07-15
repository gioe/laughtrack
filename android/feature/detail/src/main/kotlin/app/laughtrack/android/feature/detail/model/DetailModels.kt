package app.laughtrack.android.feature.detail.model

import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.core.network.generated.model.ComedianDetail
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.ShowDetail
import app.laughtrack.android.core.network.generated.model.UpcomingRun

data class ClubDetailUi(
    val detail: ClubDetail,
    val upcomingShows: List<Show>,
    val totalShows: Int,
    val currentPage: Int = 0,
) {
    val canLoadMore: Boolean get() = upcomingShows.size < totalShows
}

data class ClubShowsPage(
    val shows: List<Show>,
    val total: Int,
    val page: Int,
)

/**
 * Show-detail UI model: the generated [ShowDetail] plus its related shows and a
 * precomputed `/tickets/out` outbound link (null when the show has no ticket URL).
 * Building the URL in the repository keeps the API base URL out of the composable.
 */
data class ShowDetailUi(
    val detail: ShowDetail,
    val relatedShows: List<Show>,
    val ticketOutboundUrl: String?,
)

/**
 * Comedian-detail UI model aggregating the four endpoints behind the screen's tabs:
 * the core profile (with podcast appearances), upcoming runs + past shows (Shows
 * tab), and co-bill comedians (Related tab).
 */
data class ComedianDetailUi(
    val detail: ComedianDetail,
    val upcomingRuns: List<UpcomingRun>,
    val pastShows: List<Show>,
    val coBill: List<ComedianLineup>,
    val pinnedShows: List<Show> = emptyList(),
    val pinnedShowsTotal: Int = 0,
    val activeZip: String? = null,
    val activeLocationLabel: String? = null,
    val activeDistanceMiles: Int = 25,
)
