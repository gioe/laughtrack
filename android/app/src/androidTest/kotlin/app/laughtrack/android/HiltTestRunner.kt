package app.laughtrack.android

import android.app.Application
import android.content.Context
import androidx.test.runner.AndroidJUnitRunner
import androidx.work.Configuration
import androidx.work.WorkManager
import dagger.hilt.android.testing.HiltTestApplication

/**
 * Instrumentation runner that substitutes [HiltTestApplication] for the real
 * [LaughTrackApplication] so `@HiltAndroidTest` instrumented tests run against a
 * Hilt test graph. Wired via `testInstrumentationRunner` in app/build.gradle.kts.
 */
class HiltTestRunner : AndroidJUnitRunner() {
    override fun newApplication(
        cl: ClassLoader?,
        className: String?,
        context: Context?,
    ): Application = super.newApplication(cl, HiltTestApplication::class.java.name, context)

    override fun callApplicationOnCreate(app: Application?) {
        // The production Application initializes WorkManager on demand through
        // Configuration.Provider. HiltTestApplication cannot implement that contract,
        // so initialize the target process explicitly before its graph requests it.
        requireNotNull(app)
        WorkManager.initialize(app, Configuration.Builder().build())
        super.callApplicationOnCreate(app)
    }
}
