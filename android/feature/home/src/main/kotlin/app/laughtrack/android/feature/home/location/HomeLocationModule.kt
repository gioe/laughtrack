package app.laughtrack.android.feature.home.location

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

/**
 * Isolated Hilt binding for [HomeLocationResolver].
 *
 * Kept in its own module (rather than folded into HomeFeedModule) so instrumented /
 * screenshot tests can swap in a deterministic fake via
 * `@TestInstallIn(replaces = [HomeLocationModule::class])` without also having to
 * re-declare the unrelated HomeFeed repository/cache bindings — PersistentHomeFeedCache
 * has an `internal` constructor and cannot be re-bound from the `:app` androidTest module.
 * This is a pure DI reorganization: the production graph is unchanged.
 */
@Module
@InstallIn(SingletonComponent::class)
abstract class HomeLocationModule {
    @Binds
    abstract fun bindHomeLocationResolver(resolver: DeviceHomeLocationResolver): HomeLocationResolver
}
