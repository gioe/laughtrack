package app.laughtrack.android.core.data.favorites

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.AddFavoriteClubRequest
import app.laughtrack.android.core.network.generated.model.AddFavoritePodcastRequest
import app.laughtrack.android.core.network.generated.model.AddFavoriteRequest
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Seam for the offline favorite-replay queue so JVM unit tests can substitute a
 * recording fake: the catalog has no mocking library, and faking WorkManager
 * itself would mean implementing its full abstract surface (TASK-3659).
 */
interface FavoriteQueue {
    fun enqueue(
        entity: FavoriteEntity,
        id: String,
        isFavorite: Boolean,
    )
}

@Singleton
class FavoriteOfflineQueue
    @Inject
    constructor(
        private val workManager: WorkManager,
    ) : FavoriteQueue {
        override fun enqueue(
            entity: FavoriteEntity,
            id: String,
            isFavorite: Boolean,
        ) {
            val request =
                OneTimeWorkRequestBuilder<FavoriteReplayWorker>()
                    .setConstraints(
                        Constraints.Builder()
                            .setRequiredNetworkType(NetworkType.CONNECTED)
                            .build(),
                    )
                    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                    .setInputData(
                        workDataOf(
                            KEY_ENTITY to entity.name,
                            KEY_ID to id,
                            KEY_IS_FAVORITE to isFavorite,
                        ),
                    )
                    .build()

            workManager.enqueueUniqueWork(
                uniqueName(entity, id),
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }

        companion object {
            const val KEY_ENTITY = "entity"
            const val KEY_ID = "id"
            const val KEY_IS_FAVORITE = "isFavorite"

            fun uniqueName(
                entity: FavoriteEntity,
                id: String,
            ): String = "favorite-${entity.name.lowercase()}-$id"
        }
    }

@HiltWorker
class FavoriteReplayWorker
    @AssistedInject
    constructor(
        @Assisted appContext: Context,
        @Assisted workerParameters: WorkerParameters,
        private val favoritesApi: FavoritesApi,
    ) : CoroutineWorker(appContext, workerParameters) {
        override suspend fun doWork(): Result {
            val entity =
                inputData.getString(FavoriteOfflineQueue.KEY_ENTITY)
                    ?.let { runCatching { FavoriteEntity.valueOf(it) }.getOrNull() }
                    ?: return Result.failure()
            val id = inputData.getString(FavoriteOfflineQueue.KEY_ID) ?: return Result.failure()
            val isFavorite = inputData.getBoolean(FavoriteOfflineQueue.KEY_IS_FAVORITE, false)

            val response =
                runCatching {
                    when (entity) {
                        FavoriteEntity.COMEDIAN ->
                            if (isFavorite) {
                                favoritesApi.addFavorite(AddFavoriteRequest(id))
                            } else {
                                favoritesApi.removeFavorite(id)
                            }
                        FavoriteEntity.CLUB -> {
                            val clubId = id.toIntOrNull() ?: return Result.failure()
                            if (isFavorite) {
                                favoritesApi.addFavoriteClub(AddFavoriteClubRequest(clubId))
                            } else {
                                favoritesApi.removeFavoriteClub(clubId)
                            }
                        }
                        FavoriteEntity.PODCAST -> {
                            val podcastId = id.toIntOrNull() ?: return Result.failure()
                            if (isFavorite) {
                                favoritesApi.addFavoritePodcast(AddFavoritePodcastRequest(podcastId))
                            } else {
                                favoritesApi.removeFavoritePodcast(podcastId)
                            }
                        }
                    }
                }.getOrElse { return Result.retry() }

            return when {
                response.isSuccessful -> Result.success()
                response.code() in 400..499 -> Result.failure()
                else -> Result.retry()
            }
        }
    }
