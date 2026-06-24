package app.laughtrack.android.core.data.profile

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import app.laughtrack.android.core.network.auth.AuthProvider
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.generated.model.MeData
import app.laughtrack.android.core.network.profile.ProfileLocationUpdateRequest
import app.laughtrack.android.core.network.profile.ProfileNotificationUpdateRequest
import app.laughtrack.android.core.network.profile.ProfileSettingsApi
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.profilePreferencesDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "profile_preferences",
)

data class ProfilePreferences(
    val zipCode: String? = null,
    val nearbyDistanceMiles: Int = DEFAULT_DISTANCE_MILES,
    val emailShowNotifications: Boolean = false,
    val pushShowNotifications: Boolean = false,
) {
    companion object {
        const val DEFAULT_DISTANCE_MILES = 10
    }
}

data class ProfileAccount(
    val displayName: String?,
    val email: String,
    val avatarUrl: String?,
)

data class ProfileLocationUpdate(
    val zipCode: String?,
    val nearbyDistanceMiles: Int?,
)

data class ProfileNotificationUpdate(
    val emailShowNotifications: Boolean? = null,
    val pushShowNotifications: Boolean? = null,
)

sealed interface ProfileRefreshResult {
    data object SignedOut : ProfileRefreshResult
    data class SignedIn(val account: ProfileAccount) : ProfileRefreshResult
    data object OfflineSignedIn : ProfileRefreshResult
}

sealed interface ProfileMutationResult {
    data object Success : ProfileMutationResult
    data object InvalidZip : ProfileMutationResult
    data object SyncFailed : ProfileMutationResult
}

interface ProfileAccountService {
    fun buildSignInUrl(provider: ProfileAuthProvider): String
    suspend fun hasSession(): Boolean
    suspend fun getMe(): Result<MeData>
    suspend fun signOut(): Boolean
    suspend fun deleteAccount(): Boolean
}

enum class ProfileAuthProvider {
    GOOGLE,
    APPLE,
}

interface ProfileSettingsService {
    suspend fun updateLocation(update: ProfileLocationUpdate): Boolean
    suspend fun updateNotifications(update: ProfileNotificationUpdate): Boolean
}

interface ProfileLocalPreferences {
    val preferences: Flow<ProfilePreferences>
    suspend fun save(preferences: ProfilePreferences)
    suspend fun clear()
}

interface ProfileSessionSideEffect {
    suspend fun beforeSignOut()
}

@Singleton
class ProfileRepository @Inject constructor(
    private val accountService: ProfileAccountService,
    private val settingsService: ProfileSettingsService,
    private val localPreferences: ProfileLocalPreferences,
    private val sessionSideEffects: Set<@JvmSuppressWildcards ProfileSessionSideEffect> = emptySet(),
) {
    val preferences: Flow<ProfilePreferences> = localPreferences.preferences

    fun buildSignInUrl(provider: ProfileAuthProvider): String =
        accountService.buildSignInUrl(provider)

    suspend fun refreshSignedInProfile(): ProfileRefreshResult {
        if (!accountService.hasSession()) {
            return ProfileRefreshResult.SignedOut
        }

        return accountService.getMe().fold(
            onSuccess = { me ->
                localPreferences.save(me.toPreferences())
                ProfileRefreshResult.SignedIn(me.toAccount())
            },
            onFailure = { ProfileRefreshResult.OfflineSignedIn },
        )
    }

    suspend fun saveLocation(zipCodeDraft: String, distanceMiles: Int): ProfileMutationResult {
        val zipCode = normalizedZip(zipCodeDraft) ?: return ProfileMutationResult.InvalidZip
        val next = localPreferences.preferences.first().copy(
            zipCode = zipCode,
            nearbyDistanceMiles = distanceMiles,
        )
        localPreferences.save(next)
        val synced = settingsService.updateLocation(
            ProfileLocationUpdate(zipCode = zipCode, nearbyDistanceMiles = distanceMiles),
        )
        return if (synced) ProfileMutationResult.Success else ProfileMutationResult.SyncFailed
    }

    suspend fun clearLocation(): ProfileMutationResult {
        val next = localPreferences.preferences.first().copy(
            zipCode = null,
            nearbyDistanceMiles = ProfilePreferences.DEFAULT_DISTANCE_MILES,
        )
        localPreferences.save(next)
        val synced = settingsService.updateLocation(
            ProfileLocationUpdate(zipCode = null, nearbyDistanceMiles = null),
        )
        return if (synced) ProfileMutationResult.Success else ProfileMutationResult.SyncFailed
    }

    suspend fun setEmailNotifications(enabled: Boolean): ProfileMutationResult =
        updateNotifications { it.copy(emailShowNotifications = enabled) }

    suspend fun setPushNotifications(enabled: Boolean): ProfileMutationResult =
        updateNotifications { it.copy(pushShowNotifications = enabled) }

    suspend fun signOut(): ProfileMutationResult {
        runBeforeSignOutSideEffects()
        accountService.signOut()
        localPreferences.clear()
        return ProfileMutationResult.Success
    }

    suspend fun deleteAccount(): ProfileMutationResult {
        runBeforeSignOutSideEffects()
        if (!accountService.deleteAccount()) {
            return ProfileMutationResult.SyncFailed
        }
        localPreferences.clear()
        return ProfileMutationResult.Success
    }

    private suspend fun runBeforeSignOutSideEffects() {
        sessionSideEffects.forEach { effect ->
            runCatching { effect.beforeSignOut() }
        }
    }

    private suspend fun updateNotifications(
        nextPreferences: (ProfilePreferences) -> ProfilePreferences,
    ): ProfileMutationResult {
        val previous = localPreferences.preferences.first()
        val next = nextPreferences(previous)
        localPreferences.save(next)

        val synced = settingsService.updateNotifications(
            ProfileNotificationUpdate(
                emailShowNotifications = if (next.emailShowNotifications != previous.emailShowNotifications) {
                    next.emailShowNotifications
                } else {
                    null
                },
                pushShowNotifications = if (next.pushShowNotifications != previous.pushShowNotifications) {
                    next.pushShowNotifications
                } else {
                    null
                },
            ),
        )
        if (!synced) {
            localPreferences.save(previous)
            return ProfileMutationResult.SyncFailed
        }
        return ProfileMutationResult.Success
    }

    private fun MeData.toAccount(): ProfileAccount =
        ProfileAccount(
            displayName = displayName?.takeIf { it.isNotBlank() },
            email = email,
            avatarUrl = avatarUrl,
        )

    private fun MeData.toPreferences(): ProfilePreferences =
        ProfilePreferences(
            zipCode = zipCode?.takeIf { it.isNotBlank() },
            nearbyDistanceMiles = nearbyDistanceMiles ?: ProfilePreferences.DEFAULT_DISTANCE_MILES,
            emailShowNotifications = emailShowNotifications,
            pushShowNotifications = pushShowNotifications,
        )

    private fun normalizedZip(value: String): String? {
        val zip = value.filter(Char::isDigit).take(5)
        return zip.takeIf { it.length == 5 }
    }
}

@Singleton
class AuthSessionProfileAccountService @Inject constructor(
    private val authSessionManager: AuthSessionManager,
) : ProfileAccountService {
    override fun buildSignInUrl(provider: ProfileAuthProvider): String =
        authSessionManager.buildSignInUrl(
            when (provider) {
                ProfileAuthProvider.GOOGLE -> AuthProvider.GOOGLE
                ProfileAuthProvider.APPLE -> AuthProvider.APPLE
            },
        )

    override suspend fun hasSession(): Boolean = authSessionManager.restoreSession() != null

    override suspend fun getMe(): Result<MeData> =
        authSessionManager.getMe().map { it.data }

    override suspend fun signOut(): Boolean = authSessionManager.signOut()

    override suspend fun deleteAccount(): Boolean = authSessionManager.deleteAccount()
}

@Singleton
class NetworkProfileSettingsService @Inject constructor(
    private val profileSettingsApi: ProfileSettingsApi,
) : ProfileSettingsService {
    override suspend fun updateLocation(update: ProfileLocationUpdate): Boolean =
        profileSettingsApi.updateLocation(
            ProfileLocationUpdateRequest(
                zipCode = update.zipCode,
                nearbyDistanceMiles = update.nearbyDistanceMiles,
            ),
        ).isSuccessful

    override suspend fun updateNotifications(update: ProfileNotificationUpdate): Boolean =
        profileSettingsApi.updateNotifications(
            ProfileNotificationUpdateRequest(
                emailShowNotifications = update.emailShowNotifications,
                pushShowNotifications = update.pushShowNotifications,
            ),
        ).isSuccessful
}

@Singleton
class DataStoreProfileLocalPreferences @Inject constructor(
    @ApplicationContext context: Context,
) : ProfileLocalPreferences {
    private val dataStore = context.profilePreferencesDataStore

    override val preferences: Flow<ProfilePreferences> = dataStore.data.map { preferences ->
        ProfilePreferences(
            zipCode = preferences[Keys.zipCode],
            nearbyDistanceMiles = preferences[Keys.nearbyDistanceMiles]
                ?: ProfilePreferences.DEFAULT_DISTANCE_MILES,
            emailShowNotifications = preferences[Keys.emailShowNotifications] ?: false,
            pushShowNotifications = preferences[Keys.pushShowNotifications] ?: false,
        )
    }

    override suspend fun save(preferences: ProfilePreferences) {
        dataStore.edit { data ->
            if (preferences.zipCode == null) {
                data.remove(Keys.zipCode)
            } else {
                data[Keys.zipCode] = preferences.zipCode
            }
            data[Keys.nearbyDistanceMiles] = preferences.nearbyDistanceMiles
            data[Keys.emailShowNotifications] = preferences.emailShowNotifications
            data[Keys.pushShowNotifications] = preferences.pushShowNotifications
        }
    }

    override suspend fun clear() {
        dataStore.edit { it.clear() }
    }

    private object Keys {
        val zipCode = stringPreferencesKey("zip_code")
        val nearbyDistanceMiles = intPreferencesKey("nearby_distance_miles")
        val emailShowNotifications = booleanPreferencesKey("email_show_notifications")
        val pushShowNotifications = booleanPreferencesKey("push_show_notifications")
    }
}
