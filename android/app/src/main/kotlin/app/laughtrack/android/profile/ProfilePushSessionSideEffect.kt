package app.laughtrack.android.profile

import app.laughtrack.android.core.data.profile.ProfileSessionSideEffect
import app.laughtrack.android.push.PushTokenManager
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import dagger.multibindings.IntoSet
import javax.inject.Inject

class ProfilePushSessionSideEffect @Inject constructor(
    private val pushTokenManager: PushTokenManager,
) : ProfileSessionSideEffect {
    override suspend fun beforeSignOut() {
        pushTokenManager.deactivateCurrentToken()
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class ProfilePushSessionSideEffectModule {
    @Binds
    @IntoSet
    abstract fun bindProfilePushSessionSideEffect(
        sideEffect: ProfilePushSessionSideEffect,
    ): ProfileSessionSideEffect
}
