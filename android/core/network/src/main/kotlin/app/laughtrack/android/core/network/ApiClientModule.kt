package app.laughtrack.android.core.network

import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import javax.inject.Named
import javax.inject.Singleton

/**
 * Replaceable boundary for the generated API client and its public base URL.
 *
 * Authentication, refresh, and profile bindings remain in [NetworkModule]. Tests
 * that need a hermetic backend can replace this narrow module without copying that
 * production graph.
 */
@Module
@InstallIn(SingletonComponent::class)
object ApiClientModule {
    @Provides
    @Singleton
    fun provideApiClient(okHttpClient: OkHttpClient): ApiClient =
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        )

    /** Base URL used for outbound links that are not represented by generated APIs. */
    @Provides
    @Singleton
    @Named("apiBaseUrl")
    fun provideApiBaseUrl(): String = BuildConfig.API_BASE_URL
}
