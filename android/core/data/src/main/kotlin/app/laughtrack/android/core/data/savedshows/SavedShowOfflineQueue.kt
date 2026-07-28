package app.laughtrack.android.core.data.savedshows

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
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.api.SavedShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

interface SavedShowQueue {
    fun enqueue(
        showId: Int,
        isSaved: Boolean,
    )

    fun cancelAll()
}

@Singleton
class SavedShowOfflineQueue
    @Inject
    constructor(
        private val workManager: WorkManager,
    ) : SavedShowQueue {
        override fun enqueue(
            showId: Int,
            isSaved: Boolean,
        ) {
            val request =
                OneTimeWorkRequestBuilder<SavedShowReplayWorker>()
                    .setConstraints(
                        Constraints.Builder()
                            .setRequiredNetworkType(NetworkType.CONNECTED)
                            .build(),
                    )
                    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                    .setInputData(
                        workDataOf(
                            KEY_SHOW_ID to showId,
                            KEY_IS_SAVED to isSaved,
                        ),
                    )
                    .addTag(WORK_TAG)
                    .build()

            workManager.enqueueUniqueWork(
                uniqueName(showId),
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }

        override fun cancelAll() {
            workManager.cancelAllWorkByTag(WORK_TAG)
        }

        companion object {
            const val KEY_SHOW_ID = "showId"
            const val KEY_IS_SAVED = "isSaved"
            const val WORK_TAG = "saved-show-replay"

            fun uniqueName(showId: Int): String = "saved-show-$showId"
        }
    }

@HiltWorker
class SavedShowReplayWorker
    @AssistedInject
    constructor(
        @Assisted appContext: Context,
        @Assisted workerParameters: WorkerParameters,
        apiClient: ApiClient,
    ) : CoroutineWorker(appContext, workerParameters) {
        private val savedShowsApi = apiClient.createService(SavedShowsApi::class.java)

        override suspend fun doWork(): Result {
            val showId = inputData.getInt(SavedShowOfflineQueue.KEY_SHOW_ID, INVALID_SHOW_ID)
            if (showId <= 0) return Result.failure()
            val isSaved = inputData.getBoolean(SavedShowOfflineQueue.KEY_IS_SAVED, false)

            val response =
                runCatchingCancellable {
                    if (isSaved) {
                        savedShowsApi.saveShow(showId)
                    } else {
                        savedShowsApi.unsaveShow(showId)
                    }
                }.getOrElse { return Result.retry() }

            return when {
                response.isSuccessful -> Result.success()
                response.code() in 400..499 -> Result.failure()
                else -> Result.retry()
            }
        }

        private companion object {
            const val INVALID_SHOW_ID = -1
        }
    }
