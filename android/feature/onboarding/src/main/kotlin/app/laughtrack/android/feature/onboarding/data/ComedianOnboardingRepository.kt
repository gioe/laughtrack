package app.laughtrack.android.feature.onboarding.data

import app.laughtrack.android.core.data.favorites.FavoriteToggleResult
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.MeUpdateRequest
import java.io.IOException
import javax.inject.Inject

interface ComedianOnboardingRepository {
    suspend fun suggestions(): List<ComedianSearchItem>
    suspend fun search(query: String): List<ComedianSearchItem>
    suspend fun setFavorite(uuid: String, isFavorite: Boolean): Boolean
    suspend fun completeOnboarding()
}

class DefaultComedianOnboardingRepository @Inject constructor(
    private val comediansApi: ComediansApi,
    private val favoritesRepository: FavoritesRepository,
    private val authApi: AuthApi,
) : ComedianOnboardingRepository {
    override suspend fun suggestions(): List<ComedianSearchItem> {
        val response = comediansApi.getComedianSuggestions()
        if (!response.isSuccessful) throw IOException("Suggestions failed with HTTP ${response.code()}")
        return response.body()?.data ?: throw IOException("Suggestions returned an empty body")
    }

    override suspend fun search(query: String): List<ComedianSearchItem> {
        val response = comediansApi.searchComedians(
            comedian = query.trim().ifBlank { null },
            sort = SORT_POPULARITY,
            page = 0,
            size = SEARCH_PAGE_SIZE,
        )
        if (!response.isSuccessful) throw IOException("Search failed with HTTP ${response.code()}")
        return response.body()?.data ?: throw IOException("Search returned an empty body")
    }

    override suspend fun setFavorite(uuid: String, isFavorite: Boolean): Boolean =
        when (val result = favoritesRepository.setComedianFavorite(uuid, isFavorite)) {
            is FavoriteToggleResult.Updated -> result.isFavorite
            is FavoriteToggleResult.Queued -> result.isFavorite
            is FavoriteToggleResult.Failure -> throw IOException(result.message)
        }

    override suspend fun completeOnboarding() {
        val response = authApi.updateMe(MeUpdateRequest(comedianOnboardingCompleted = true))
        if (!response.isSuccessful) {
            throw IOException("PATCH /me failed with HTTP ${response.code()}")
        }
    }

    private companion object {
        const val SEARCH_PAGE_SIZE = 12
        const val SORT_POPULARITY = "popularity"
    }
}
