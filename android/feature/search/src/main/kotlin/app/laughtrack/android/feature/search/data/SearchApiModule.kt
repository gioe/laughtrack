package app.laughtrack.android.feature.search.data

import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Provides the generated search services from the shared configured [ApiClient]
 * (core:network). Each search endpoint is public (optional-auth), so the standard
 * authed client is fine — the interceptor simply omits the Bearer header when no
 * session exists.
 */
@Module
@InstallIn(SingletonComponent::class)
object SearchApiModule {
    @Provides
    @Singleton
    fun provideShowsApi(apiClient: ApiClient): ShowsApi =
        apiClient.createService(ShowsApi::class.java)

    @Provides
    @Singleton
    fun provideClubsApi(apiClient: ApiClient): ClubsApi =
        apiClient.createService(ClubsApi::class.java)

    @Provides
    @Singleton
    fun providePodcastsApi(apiClient: ApiClient): PodcastsApi =
        apiClient.createService(PodcastsApi::class.java)
}
