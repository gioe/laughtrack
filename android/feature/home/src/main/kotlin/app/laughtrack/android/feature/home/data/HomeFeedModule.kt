package app.laughtrack.android.feature.home.data

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
abstract class HomeFeedModule {
    @Binds
    abstract fun bindHomeFeedRepository(repository: DefaultHomeFeedRepository): HomeFeedRepository
}
