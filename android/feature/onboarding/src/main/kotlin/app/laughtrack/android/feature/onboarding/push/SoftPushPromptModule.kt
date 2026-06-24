package app.laughtrack.android.feature.onboarding.push

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class SoftPushPromptModule {
    @Binds
    @Singleton
    abstract fun bindSoftPushPromptCoordinator(
        coordinator: DefaultSoftPushPromptCoordinator,
    ): SoftPushPromptCoordinator
}
