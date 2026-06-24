package app.laughtrack.android.push

import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Provides the hand-rolled [PushTokenApi] from the shared authed [ApiClient].
 * [PushTokenManager] is constructor-injected (@Inject), so Hilt builds it directly.
 */
@Module
@InstallIn(SingletonComponent::class)
object PushModule {
    @Provides
    @Singleton
    fun providePushTokenApi(apiClient: ApiClient): PushTokenApi =
        apiClient.createService(PushTokenApi::class.java)
}
