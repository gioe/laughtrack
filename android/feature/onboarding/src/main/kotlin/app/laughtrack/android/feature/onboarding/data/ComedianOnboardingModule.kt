package app.laughtrack.android.feature.onboarding.data

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
abstract class ComedianOnboardingModule {
    @Binds
    abstract fun bindComedianOnboardingRepository(
        repository: DefaultComedianOnboardingRepository,
    ): ComedianOnboardingRepository
}
