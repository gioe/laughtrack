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

    @Binds
    abstract fun bindHomeFeedCache(cache: PersistentHomeFeedCache): HomeFeedCache

    // HomeLocationResolver is bound in HomeLocationModule so tests can replace just
    // that binding without touching the repository/cache bindings above.
}
