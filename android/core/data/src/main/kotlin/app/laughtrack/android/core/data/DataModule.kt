package app.laughtrack.android.core.data

import android.content.Context
import androidx.work.WorkManager
import app.laughtrack.android.core.data.favorites.FavoriteOfflineQueue
import app.laughtrack.android.core.data.favorites.FavoriteQueue
import app.laughtrack.android.core.data.profile.AuthSessionProfileAccountService
import app.laughtrack.android.core.data.profile.DataStoreProfileLocalPreferences
import app.laughtrack.android.core.data.profile.NetworkProfileSettingsService
import app.laughtrack.android.core.data.profile.ProfileAccountService
import app.laughtrack.android.core.data.profile.ProfileLocalPreferences
import app.laughtrack.android.core.data.profile.ProfileSettingsService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Suppress("unused")
@Module
@InstallIn(SingletonComponent::class)
object DataModule {
    @Provides
    @Singleton
    fun provideWorkManager(
        @ApplicationContext context: Context,
    ): WorkManager = WorkManager.getInstance(context)

    @Provides
    @Singleton
    fun provideFavoriteQueue(queue: FavoriteOfflineQueue): FavoriteQueue = queue

    @Provides
    @Singleton
    fun provideProfileAccountService(service: AuthSessionProfileAccountService): ProfileAccountService = service

    @Provides
    @Singleton
    fun provideProfileSettingsService(service: NetworkProfileSettingsService): ProfileSettingsService = service

    @Provides
    @Singleton
    fun provideProfileLocalPreferences(preferences: DataStoreProfileLocalPreferences): ProfileLocalPreferences =
        preferences
}
