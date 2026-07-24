package app.laughtrack.android.feature.profile

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.CurrentLocationResolver
import app.laughtrack.android.core.data.location.CurrentLocationResult
import app.laughtrack.android.core.data.profile.ProfileAccountService
import app.laughtrack.android.core.data.profile.ProfileAuthProvider
import app.laughtrack.android.core.data.profile.ProfileLocalPreferences
import app.laughtrack.android.core.data.profile.ProfileLocationUpdate
import app.laughtrack.android.core.data.profile.ProfileNotificationUpdate
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.data.profile.ProfileRepository
import app.laughtrack.android.core.data.profile.ProfileSettingsService
import app.laughtrack.android.core.network.generated.model.MeData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProfileViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun refresh_with_session_publishes_signed_in_account() =
        runTest {
            val viewModel = viewModel(FakeProfileAccountService(hasSession = true, me = meData()))
            subscribe(viewModel)

            viewModel.refresh()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertTrue(state.signedIn)
            assertEquals("ada@example.com", state.account?.email)
            assertFalse(state.isLoading)
            assertNull(state.message)
        }

    @Test
    fun refresh_without_session_resets_to_signed_out() =
        runTest {
            val viewModel = viewModel(FakeProfileAccountService(hasSession = false))
            subscribe(viewModel)

            viewModel.refresh()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertFalse(state.signedIn)
            assertNull(state.account)
            assertFalse(state.isLoading)
        }

    @Test
    fun refresh_offline_keeps_signed_in_with_stale_profile_message() =
        runTest {
            // Session exists but /me fails: the user stays signed in with a notice.
            val viewModel = viewModel(FakeProfileAccountService(hasSession = true, me = null))
            subscribe(viewModel)

            viewModel.refresh()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertTrue(state.signedIn)
            assertEquals("Signed in. Latest profile details are unavailable.", state.message)
        }

    @Test
    fun sign_out_resets_state_and_reports_message() =
        runTest {
            val accountService = FakeProfileAccountService(hasSession = true, me = meData())
            val viewModel = viewModel(accountService)
            subscribe(viewModel)
            viewModel.refresh()
            advanceUntilIdle()

            viewModel.signOut()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertTrue(accountService.signOutCalled)
            assertFalse(state.signedIn)
            assertNull(state.account)
            assertEquals("Signed out.", state.message)
            assertFalse(state.isMutating)
        }

    @Test
    fun delete_account_success_resets_state_and_reports_message() =
        runTest {
            val accountService = FakeProfileAccountService(hasSession = true, me = meData())
            val viewModel = viewModel(accountService)
            subscribe(viewModel)
            viewModel.refresh()
            advanceUntilIdle()
            viewModel.requestDeleteAccount()

            viewModel.deleteAccount()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertTrue(accountService.deleteCalled)
            assertFalse(state.signedIn)
            assertEquals("Account deleted.", state.message)
            assertFalse(state.showDeleteConfirmation)
        }

    @Test
    fun delete_account_failure_keeps_session_and_surfaces_error() =
        runTest {
            val accountService =
                FakeProfileAccountService(hasSession = true, me = meData(), deleteSucceeds = false)
            val viewModel = viewModel(accountService)
            subscribe(viewModel)
            viewModel.refresh()
            advanceUntilIdle()
            viewModel.requestDeleteAccount()

            viewModel.deleteAccount()
            advanceUntilIdle()

            val state = viewModel.uiState.value
            assertTrue(state.signedIn)
            assertEquals("Could not delete your account. Please try again.", state.message)
            assertFalse(state.showDeleteConfirmation)
            assertFalse(state.isMutating)
        }

    @Test
    fun save_location_with_invalid_zip_surfaces_validation_message_without_syncing() =
        runTest {
            val settingsService = FakeProfileSettingsService()
            val viewModel = viewModel(settingsService = settingsService)
            subscribe(viewModel)

            viewModel.setZipCodeDraft("123")
            viewModel.saveLocation()
            advanceUntilIdle()

            assertEquals("Enter a valid 5-digit ZIP code.", viewModel.uiState.value.message)
            assertTrue(settingsService.locationUpdates.isEmpty())
        }

    @Test
    fun current_location_resolution_persists_zip_and_distance() =
        runTest {
            val settingsService = FakeProfileSettingsService()
            val viewModel =
                viewModel(
                    settingsService = settingsService,
                    currentLocationResult = CurrentLocationResult.Success("10001"),
                )
            subscribe(viewModel)

            viewModel.setSelectedDistance(50)
            viewModel.useCurrentLocation()
            advanceUntilIdle()

            assertEquals(
                ProfileLocationUpdate(zipCode = "10001", nearbyDistanceMiles = 50),
                settingsService.locationUpdates.single(),
            )
            assertEquals("10001", viewModel.uiState.value.preferences.zipCode)
            assertEquals("10001", viewModel.uiState.value.zipCodeDraft)
            assertEquals("Current location saved to your profile.", viewModel.uiState.value.message)
            assertFalse(viewModel.uiState.value.isResolvingCurrentLocation)
        }

    @Test
    fun current_location_failures_preserve_manual_zip_and_surface_recovery_feedback() =
        runTest {
            val failures =
                listOf(
                    CurrentLocationResult.PermissionDenied to
                        "Location permission was denied. You can still enter a ZIP code.",
                    CurrentLocationResult.LocationUnavailable to
                        "Your current location is unavailable. You can still enter a ZIP code.",
                    CurrentLocationResult.GeocodingFailed to
                        "We could not find a ZIP code for your location. Try again or enter one manually.",
                )

            failures.forEach { (result, expectedMessage) ->
                val settingsService = FakeProfileSettingsService()
                val viewModel =
                    viewModel(
                        settingsService = settingsService,
                        currentLocationResult = result,
                    )
                subscribe(viewModel)
                viewModel.setZipCodeDraft("90210")

                viewModel.useCurrentLocation()
                advanceUntilIdle()

                assertEquals("90210", viewModel.uiState.value.zipCodeDraft)
                assertEquals(expectedMessage, viewModel.uiState.value.message)
                assertFalse(viewModel.uiState.value.isResolvingCurrentLocation)
                assertTrue(settingsService.locationUpdates.isEmpty())
            }
        }

    @Test
    fun failed_notification_save_surfaces_the_sync_error() =
        runTest {
            val settingsService = FakeProfileSettingsService(succeeds = false)
            val viewModel = viewModel(settingsService = settingsService)
            subscribe(viewModel)

            viewModel.setEmailNotifications(true)
            advanceUntilIdle()

            assertEquals(
                "LaughTrack could not save that alert preference.",
                viewModel.uiState.value.message,
            )
            assertEquals(1, settingsService.notificationUpdates.size)
        }

    // -- helpers ----------------------------------------------------------------

    /** uiState is stateIn(WhileSubscribed): the combine only runs while collected. */
    private fun TestScope.subscribe(viewModel: ProfileViewModel) {
        backgroundScope.launch { viewModel.uiState.collect {} }
    }

    private fun viewModel(
        accountService: ProfileAccountService = FakeProfileAccountService(hasSession = false),
        settingsService: ProfileSettingsService = FakeProfileSettingsService(),
        currentLocationResult: CurrentLocationResult = CurrentLocationResult.LocationUnavailable,
    ): ProfileViewModel =
        ProfileViewModel(
            repository =
                ProfileRepository(
                    accountService = accountService,
                    settingsService = settingsService,
                    localPreferences = FakeLocalPreferences(),
                    sessionSideEffects = emptySet(),
                ),
            analytics = AnalyticsManager(emptyList()),
            currentLocationResolver = FakeCurrentLocationResolver(currentLocationResult),
        )

    private fun meData() =
        MeData(
            userId = "test-user-id",
            email = "ada@example.com",
            isAdmin = false,
            emailShowNotifications = false,
            pushShowNotifications = false,
            comedianOnboardingCompleted = true,
            zipCode = "94108",
            nearbyDistanceMiles = 25,
            displayName = "Ada Lovelace",
            avatarUrl = "https://example.com/ada.jpg",
        )

    private class FakeProfileAccountService(
        private val hasSession: Boolean,
        private val me: MeData? = null,
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
            me?.let { Result.success(it) }
                ?: Result.failure<MeData>(IllegalStateException("offline"))

        override suspend fun signOut(): Boolean {
            signOutCalled = true
            // The ViewModel resets state regardless of the result, so there is no
            // failure branch to exercise here.
            return true
        }

        override suspend fun deleteAccount(): Boolean {
            deleteCalled = true
            return deleteSucceeds
        }
    }

    private class FakeProfileSettingsService(
        private val succeeds: Boolean = true,
    ) : ProfileSettingsService {
        val locationUpdates = mutableListOf<ProfileLocationUpdate>()
        val notificationUpdates = mutableListOf<ProfileNotificationUpdate>()

        override suspend fun updateLocation(update: ProfileLocationUpdate): Boolean {
            locationUpdates += update
            return succeeds
        }

        override suspend fun updateNotifications(update: ProfileNotificationUpdate): Boolean {
            notificationUpdates += update
            return succeeds
        }
    }

    private class FakeCurrentLocationResolver(
        private val result: CurrentLocationResult,
    ) : CurrentLocationResolver {
        override suspend fun resolve(): CurrentLocationResult = result
    }

    private class FakeLocalPreferences : ProfileLocalPreferences {
        private val state = MutableStateFlow(ProfilePreferences())
        override val preferences: Flow<ProfilePreferences> = state

        override suspend fun save(preferences: ProfilePreferences) {
            state.value = preferences
        }

        override suspend fun clear() {
            state.value = ProfilePreferences()
        }
    }
}
