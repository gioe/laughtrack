package app.laughtrack.android.feature.onboarding.push

import android.content.Context
import android.content.SharedPreferences
import dagger.hilt.android.qualifiers.ApplicationContext
import java.time.Clock
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

interface SoftPushPromptCoordinator {
    suspend fun onFavoriteAdded(): Boolean

    suspend fun deferPrompt()
}

@Singleton
class DefaultSoftPushPromptCoordinator
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) : SoftPushPromptCoordinator {
        private val clock: Clock = Clock.systemUTC()
        private val preferences: SharedPreferences =
            context.getSharedPreferences("soft_push_prompt", Context.MODE_PRIVATE)
        private var hasPresentedThisSession = false

        override suspend fun onFavoriteAdded(): Boolean {
            if (hasPresentedThisSession) return false
            val nextCount = preferences.getInt(KEY_ENGAGEMENT_COUNT, 0) + 1
            preferences.edit().putInt(KEY_ENGAGEMENT_COUNT, nextCount).apply()

            val decision =
                PushPromptCadence.evaluate(
                    PushPromptCadence.Input(
                        now = clock.instant(),
                        deferralCount = preferences.getInt(KEY_DEFERRAL_COUNT, 0),
                        lastDeferredAt =
                            preferences.getLong(KEY_LAST_DEFERRED_AT, 0L)
                                .takeIf { it > 0L }
                                ?.let(Instant::ofEpochMilli),
                        engagementCount = nextCount,
                        hasPresentedThisSession = hasPresentedThisSession,
                    ),
                )
            if (decision == PushPromptCadence.Decision.Eligible) {
                hasPresentedThisSession = true
                return true
            }
            return false
        }

        override suspend fun deferPrompt() {
            preferences.edit()
                .putInt(KEY_DEFERRAL_COUNT, preferences.getInt(KEY_DEFERRAL_COUNT, 0) + 1)
                .putLong(KEY_LAST_DEFERRED_AT, clock.millis())
                .apply()
        }

        private companion object {
            const val KEY_ENGAGEMENT_COUNT = "post_onboarding_favorite_count"
            const val KEY_DEFERRAL_COUNT = "deferral_count"
            const val KEY_LAST_DEFERRED_AT = "last_deferred_at"
        }
    }
