package app.laughtrack.android.core.data.profile

import app.laughtrack.android.core.network.generated.model.MeData
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProfileRepositoryTest {
    @Test
    fun refreshSignedInProfile_hydratesAccountAndLocalPreferencesFromMe() = runTest {
        val accountService = FakeProfileAccountService(
            hasSession = true,
            me = profile(emailShowNotifications = true, pushShowNotifications = true),
        )
        val localPreferences = FakeLocalPreferences()
        val repository = ProfileRepository(
            accountService = accountService,
            settingsService = FakeProfileSettingsService(),
            localPreferences = localPreferences,
        )

        val result = repository.refreshSignedInProfile()

        assertTrue(result is ProfileRefreshResult.SignedIn)
        result as ProfileRefreshResult.SignedIn
        assertEquals("Ada Lovelace", result.account.displayName)
        assertEquals("ada@example.com", result.account.email)
        assertEquals("https://example.com/ada.jpg", result.account.avatarUrl)
        assertEquals(
            ProfilePreferences(
                zipCode = "94108",
                nearbyDistanceMiles = 25,
                emailShowNotifications = true,
                pushShowNotifications = true,
            ),
            localPreferences.preferences.first(),
        )
    }

    @Test
    fun saveLocation_persistsNormalizedZipAndSyncsServer() = runTest {
        val settingsService = FakeProfileSettingsService()
        val localPreferences = FakeLocalPreferences()
        val repository = ProfileRepository(
            accountService = FakeProfileAccountService(hasSession = true),
            settingsService = settingsService,
            localPreferences = localPreferences,
        )

        val result = repository.saveLocation("94108-1234", 50)

        assertEquals(ProfileMutationResult.Success, result)
        assertEquals("94108", localPreferences.preferences.first().zipCode)
        assertEquals(50, localPreferences.preferences.first().nearbyDistanceMiles)
        assertEquals(ProfileLocationUpdate("94108", 50), settingsService.locationUpdates.single())
    }

    @Test
    fun saveLocation_rejectsInvalidZipWithoutPersistingOrSyncing() = runTest {
        val settingsService = FakeProfileSettingsService()
        val localPreferences = FakeLocalPreferences()
        val repository = ProfileRepository(
            accountService = FakeProfileAccountService(hasSession = true),
            settingsService = settingsService,
            localPreferences = localPreferences,
        )

        val result = repository.saveLocation("abc", 25)

        assertEquals(ProfileMutationResult.InvalidZip, result)
        assertEquals(ProfilePreferences(), localPreferences.preferences.first())
        assertTrue(settingsService.locationUpdates.isEmpty())
    }

    @Test
    fun setEmailNotifications_revertsLocalPreferenceWhenServerSyncFails() = runTest {
        val settingsService = FakeProfileSettingsService(notificationUpdateSucceeds = false)
        val localPreferences = FakeLocalPreferences(
            ProfilePreferences(emailShowNotifications = false),
        )
        val repository = ProfileRepository(
            accountService = FakeProfileAccountService(hasSession = true),
            settingsService = settingsService,
            localPreferences = localPreferences,
        )

        val result = repository.setEmailNotifications(true)

        assertEquals(ProfileMutationResult.SyncFailed, result)
        assertFalse(localPreferences.preferences.first().emailShowNotifications)
        assertEquals(ProfileNotificationUpdate(emailShowNotifications = true), settingsService.notificationUpdates.single())
    }

    @Test
    fun signOut_clearsLocalAccountAndPreferencesEvenWhenServerRevocationFails() = runTest {
        val accountService = FakeProfileAccountService(hasSession = true, signOutSucceeds = false)
        val localPreferences = FakeLocalPreferences(ProfilePreferences(zipCode = "94108"))
        val repository = ProfileRepository(
            accountService = accountService,
            settingsService = FakeProfileSettingsService(),
            localPreferences = localPreferences,
        )

        val result = repository.signOut()

        assertEquals(ProfileMutationResult.Success, result)
        assertTrue(accountService.signOutCalled)
        assertEquals(ProfilePreferences(), localPreferences.preferences.first())
    }

    @Test
    fun deleteAccountOnlyClearsLocalStateAfterSuccessfulServerDeletion() = runTest {
        val accountService = FakeProfileAccountService(hasSession = true, deleteSucceeds = false)
        val localPreferences = FakeLocalPreferences(ProfilePreferences(zipCode = "94108"))
        val repository = ProfileRepository(
            accountService = accountService,
            settingsService = FakeProfileSettingsService(),
            localPreferences = localPreferences,
        )

        val result = repository.deleteAccount()

        assertEquals(ProfileMutationResult.SyncFailed, result)
        assertTrue(accountService.deleteCalled)
        assertEquals("94108", localPreferences.preferences.first().zipCode)
    }

    private fun profile(
        emailShowNotifications: Boolean = false,
        pushShowNotifications: Boolean = false,
    ) = MeData(
        email = "ada@example.com",
        isAdmin = false,
        emailShowNotifications = emailShowNotifications,
        pushShowNotifications = pushShowNotifications,
        comedianOnboardingCompleted = true,
        zipCode = "94108",
        nearbyDistanceMiles = 25,
        displayName = "Ada Lovelace",
        avatarUrl = "https://example.com/ada.jpg",
    )
}

private class FakeProfileAccountService(
    private val hasSession: Boolean,
    private val me: MeData? = null,
    private val signOutSucceeds: Boolean = true,
    private val deleteSucceeds: Boolean = true,
) : ProfileAccountService {
    var signOutCalled = false
        private set
    var deleteCalled = false
        private set

    override fun buildSignInUrl(provider: ProfileAuthProvider): String =
        "https://example.com/sign-in/${provider.name.lowercase()}"

    override suspend fun hasSession(): Boolean = hasSession

    override suspend fun getMe(): Result<MeData> =
        me?.let { Result.success(it) } ?: Result.failure(IllegalStateException("No profile"))

    override suspend fun signOut(): Boolean {
        signOutCalled = true
        return signOutSucceeds
    }

    override suspend fun deleteAccount(): Boolean {
        deleteCalled = true
        return deleteSucceeds
    }
}

private class FakeProfileSettingsService(
    private val locationUpdateSucceeds: Boolean = true,
    private val notificationUpdateSucceeds: Boolean = true,
) : ProfileSettingsService {
    val locationUpdates = mutableListOf<ProfileLocationUpdate>()
    val notificationUpdates = mutableListOf<ProfileNotificationUpdate>()

    override suspend fun updateLocation(update: ProfileLocationUpdate): Boolean {
        locationUpdates += update
        return locationUpdateSucceeds
    }

    override suspend fun updateNotifications(update: ProfileNotificationUpdate): Boolean {
        notificationUpdates += update
        return notificationUpdateSucceeds
    }
}

private class FakeLocalPreferences(
    initial: ProfilePreferences = ProfilePreferences(),
) : ProfileLocalPreferences {
    private val state = MutableStateFlow(initial)
    override val preferences: Flow<ProfilePreferences> = state

    override suspend fun save(preferences: ProfilePreferences) {
        state.value = preferences
    }

    override suspend fun clear() {
        state.value = ProfilePreferences()
    }
}
