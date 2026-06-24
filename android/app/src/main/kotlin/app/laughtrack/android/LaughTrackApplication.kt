package app.laughtrack.android

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

/**
 * Application entry point. [HiltAndroidApp] generates the Hilt dependency-injection
 * container that backs every Activity, ViewModel, and service in the app — the
 * Android analog of the iOS app's service container / bootstrap.
 */
@HiltAndroidApp
class LaughTrackApplication : Application(), Configuration.Provider {
    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}
