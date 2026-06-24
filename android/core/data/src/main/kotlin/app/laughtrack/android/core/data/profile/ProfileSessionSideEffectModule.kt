package app.laughtrack.android.core.data.profile

import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import dagger.multibindings.Multibinds

@Module
@InstallIn(SingletonComponent::class)
abstract class ProfileSessionSideEffectModule {
    @Multibinds
    abstract fun profileSessionSideEffects(): Set<ProfileSessionSideEffect>
}
