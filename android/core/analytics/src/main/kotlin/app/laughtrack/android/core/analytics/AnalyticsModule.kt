package app.laughtrack.android.core.analytics

import android.content.Context
import android.content.pm.ApplicationInfo
import com.google.firebase.FirebaseApp
import com.google.firebase.analytics.FirebaseAnalytics
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Builds the active [AnalyticsProvider] list, mirroring the iOS provider selection:
 * a Firebase provider only when a Firebase project is configured (no
 * google-services.json → FirebaseApp never initializes → analytics stay dormant),
 * plus a console provider on debuggable builds. An empty list makes
 * [AnalyticsManager] a silent no-op.
 */
@Module
@InstallIn(SingletonComponent::class)
object AnalyticsModule {
    @Provides
    @Singleton
    fun provideAnalyticsProviders(
        @ApplicationContext context: Context,
    ): List<AnalyticsProvider> = buildList {
        if (FirebaseApp.getApps(context).isNotEmpty()) {
            add(FirebaseAnalyticsProvider(FirebaseAnalytics.getInstance(context)))
        }
        val debuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        if (debuggable) {
            add(ConsoleAnalyticsProvider())
        }
    }
}
