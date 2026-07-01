package app.laughtrack.android.feature.home.data

import app.laughtrack.android.feature.home.location.DeviceHomeLocationResolver
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
abstract class HomeFeedModule {
    @Binds
    abstract fun bindHomeFeedRepository(repository: DefaultHomeFeedRepository): HomeFeedRepository

    @Binds
    abstract fun bindHomeFeedCache(cache: PersistentHomeFeedCache): HomeFeedCache

    @Binds
    abstract fun bindHomeLocationResolver(resolver: DeviceHomeLocationResolver): HomeLocationResolver
}
