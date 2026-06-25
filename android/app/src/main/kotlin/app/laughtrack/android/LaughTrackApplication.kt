package app.laughtrack.android

import android.app.Application
import android.content.pm.ApplicationInfo
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import io.sentry.android.core.SentryAndroid
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
        get() =
            Configuration.Builder()
                .setWorkerFactory(workerFactory)
                .build()

    override fun onCreate() {
        super.onCreate()
        initSentry()
    }

    /**
     * Initialize Sentry only when a DSN was injected at build time (release builds
     * via -PsentryDsn / a CI secret). With no DSN the SDK stays dormant, mirroring
     * the gated Firebase config — no crash reports are sent until provisioned.
     *
     * This is the ONLY Sentry initialization path: the SDK's auto-init
     * ContentProviders (SentryInitProvider/SentryPerformanceProvider) are stripped
     * from the merged manifest via `tools:node="remove"` in AndroidManifest.xml,
     * because auto-init crashes any DSN-less build at startup. If this method is
     * ever removed or short-circuited, Sentry silently stops capturing — there is
     * no provider fallback. Keep the manifest removal and this method in sync.
     */
    private fun initSentry() {
        val dsn = BuildConfig.SENTRY_DSN
        if (dsn.isBlank()) return
        val debuggable = (applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        SentryAndroid.init(this) { options ->
            options.dsn = dsn
            options.release = BuildConfig.VERSION_NAME
            options.environment = if (debuggable) "debug" else "production"
        }
    }
}
