package app.laughtrack.android.core.network

import android.content.Context
import android.os.Build
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
        @ApplicationContext context: Context,
        tokenStore: TokenStore,
        authApi: AuthApi,
    ): AuthSessionManager =
        AuthSessionManager(
            tokenStore = tokenStore,
            authApi = authApi,
            appVersion = appVersion(context),
            websiteBaseUrl =
                BuildConfig.API_BASE_URL
                    .removeSuffix("/api/v1/")
                    .removeSuffix("/api/v1"),
        )

    private fun appVersion(context: Context): String =
        runCatching {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            val buildNumber =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    packageInfo.longVersionCode
                } else {
                    @Suppress("DEPRECATION")
                    packageInfo.versionCode.toLong()
                }
            "${packageInfo.versionName ?: "0"}+$buildNumber"
        }.getOrDefault("0")

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
