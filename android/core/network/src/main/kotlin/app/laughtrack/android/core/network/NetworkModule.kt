package app.laughtrack.android.core.network

import android.content.Context
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.AuthTokenInterceptor
import app.laughtrack.android.core.network.auth.EncryptedSharedPreferencesTokenStore
import app.laughtrack.android.core.network.auth.RefreshTokenAuthenticator
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.profile.ProfileSettingsApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import javax.inject.Named
import javax.inject.Singleton

@Suppress("unused")
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideTokenStore(
        @ApplicationContext context: Context,
    ): TokenStore = EncryptedSharedPreferencesTokenStore(context)

    @Provides
    @Singleton
    fun provideAuthTokenInterceptor(tokenStore: TokenStore): AuthTokenInterceptor = AuthTokenInterceptor(tokenStore)

    @Provides
    @Singleton
    @Named("refresh")
    fun provideRefreshOkHttpClient(): OkHttpClient = baseOkHttpBuilder().build()

    @Provides
    @Singleton
    @Named("refresh")
    fun provideRefreshAuthApi(
        @Named("refresh") okHttpClient: OkHttpClient,
    ): AuthApi =
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        ).createService(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideRefreshTokenAuthenticator(
        tokenStore: TokenStore,
        @Named("refresh") refreshAuthApi: AuthApi,
    ): RefreshTokenAuthenticator =
        RefreshTokenAuthenticator(
            tokenStore = tokenStore,
            refreshApi = refreshAuthApi,
        )

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authTokenInterceptor: AuthTokenInterceptor,
        refreshTokenAuthenticator: RefreshTokenAuthenticator,
    ): OkHttpClient =
        baseOkHttpBuilder()
            .addInterceptor(authTokenInterceptor)
            .authenticator(refreshTokenAuthenticator)
            .build()

    /**
     * Shared, fully-configured [ApiClient] (auth interceptor + refresh + X-Timezone,
     * base URL). Feature modules build their own generated services from it, e.g.
     * `apiClient.createService(ShowsApi::class.java)`, instead of reaching into
     * this module's BuildConfig.
     */
    @Provides
    @Singleton
    fun provideApiClient(okHttpClient: OkHttpClient): ApiClient =
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        )

    /**
     * The configured API base URL (e.g. `https://www.laugh-track.com/api/v1`) for
     * feature modules that need to build raw outbound links the typed client does
     * not model — notably the Show-detail `/tickets/out` redirect, which logs the
     * ticket click and 302-redirects to the venue. Exposed so features don't reach
     * into this module's `BuildConfig` directly.
     */
    @Provides
    @Singleton
    @Named("apiBaseUrl")
    fun provideApiBaseUrl(): String = BuildConfig.API_BASE_URL

    @Provides
    @Singleton
    fun provideAuthApi(okHttpClient: OkHttpClient): AuthApi =
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        ).createService(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideFavoritesApi(okHttpClient: OkHttpClient): FavoritesApi =
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            okHttpClientBuilder = okHttpClient.newBuilder(),
        ).createService(FavoritesApi::class.java)

    @Provides
    @Singleton
    fun provideComediansApi(apiClient: ApiClient): ComediansApi = apiClient.createService(ComediansApi::class.java)

    @Provides
    @Singleton
    fun provideProfileSettingsApi(apiClient: ApiClient): ProfileSettingsApi =
        apiClient.createService(ProfileSettingsApi::class.java)

    @Provides
    @Singleton
    fun provideAuthSessionManager(
        tokenStore: TokenStore,
        authApi: AuthApi,
    ): AuthSessionManager =
        AuthSessionManager(
            tokenStore = tokenStore,
            authApi = authApi,
            websiteBaseUrl =
                BuildConfig.API_BASE_URL
                    .removeSuffix("/api/v1/")
                    .removeSuffix("/api/v1"),
        )

    private fun baseOkHttpBuilder(): OkHttpClient.Builder {
        val loggingLevel =
            if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BASIC
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        return OkHttpClient.Builder()
            .retryOnConnectionFailure(true)
            .addNetworkInterceptor(
                HttpLoggingInterceptor().apply {
                    level = loggingLevel
                },
            )
    }
}
