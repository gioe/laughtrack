package app.laughtrack.android.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.CurrentLocationResolver
import app.laughtrack.android.core.data.location.CurrentLocationResult
import app.laughtrack.android.core.data.profile.ProfileAccount
import app.laughtrack.android.core.data.profile.ProfileAuthProvider
import app.laughtrack.android.core.data.profile.ProfileMutationResult
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.data.profile.ProfileRefreshResult
import app.laughtrack.android.core.data.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val signedIn: Boolean = false,
    val account: ProfileAccount? = null,
    val preferences: ProfilePreferences = ProfilePreferences(),
    val zipCodeDraft: String = "",
    val selectedDistanceMiles: Int = ProfilePreferences.DEFAULT_DISTANCE_MILES,
    val isLoading: Boolean = true,
    val isMutating: Boolean = false,
    val isResolvingCurrentLocation: Boolean = false,
    val message: String? = null,
    val showSignOutConfirmation: Boolean = false,
    val showDeleteConfirmation: Boolean = false,
    val zipCodeDraftTouched: Boolean = false,
    val distanceTouched: Boolean = false,
)

@HiltViewModel
class ProfileViewModel
    @Inject
    constructor(
        private val repository: ProfileRepository,
        private val analytics: AnalyticsManager,
        private val currentLocationResolver: CurrentLocationResolver,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(ProfileUiState())

        val uiState: StateFlow<ProfileUiState> =
            combine(
                mutableState,
                repository.preferences,
            ) { state, preferences ->
                state.copy(
                    preferences = preferences,
                    zipCodeDraft =
                        if (state.zipCodeDraftTouched) {
                            state.zipCodeDraft
                        } else {
                            preferences.zipCode.orEmpty()
                        },
                    selectedDistanceMiles =
                        if (state.distanceTouched) {
                            state.selectedDistanceMiles
                        } else {
                            preferences.nearbyDistanceMiles
                        },
                )
            }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ProfileUiState())

        fun buildGoogleSignInUrl(): String = repository.buildSignInUrl(ProfileAuthProvider.GOOGLE)

        fun buildAppleSignInUrl(): String = repository.buildSignInUrl(ProfileAuthProvider.APPLE)

        fun buildEmailSignInUrl(): String = repository.buildSignInUrl(ProfileAuthProvider.EMAIL)

        fun refresh() {
            viewModelScope.launch {
                mutableState.update { it.copy(isLoading = true, message = null) }
                when (val result = repository.refreshSignedInProfile()) {
                    is ProfileRefreshResult.SignedIn -> {
                        mutableState.update {
                            it.copy(
                                signedIn = true,
                                account = result.account,
                                isLoading = false,
                                message = null,
                            )
                        }
                    }
                    ProfileRefreshResult.OfflineSignedIn -> {
                        mutableState.update {
                            it.copy(
                                signedIn = true,
                                isLoading = false,
                                message = "Signed in. Latest profile details are unavailable.",
                            )
                        }
                    }
                    ProfileRefreshResult.SignedOut -> {
                        mutableState.update {
                            ProfileUiState(isLoading = false)
                        }
                    }
                }
            }
        }

        fun setZipCodeDraft(value: String) {
            mutableState.update {
                it.copy(
                    zipCodeDraft = value.filter(Char::isDigit).take(5),
                    zipCodeDraftTouched = true,
                )
            }
        }

        fun setSelectedDistance(distanceMiles: Int) {
            mutableState.update {
                it.copy(selectedDistanceMiles = distanceMiles, distanceTouched = true)
            }
        }

        fun saveLocation() {
            mutate(resetLocationDrafts = true) {
                when (repository.saveLocation(uiState.value.zipCodeDraft, uiState.value.selectedDistanceMiles)) {
                    ProfileMutationResult.Success -> "Profile location saved."
                    ProfileMutationResult.InvalidZip -> "Enter a valid 5-digit ZIP code."
                    ProfileMutationResult.SyncFailed -> "LaughTrack could not save that profile location."
                }
            }
        }

        fun useCurrentLocation() {
            viewModelScope.launch {
                mutableState.update {
                    it.copy(isResolvingCurrentLocation = true, message = null)
                }
                when (val result = currentLocationResolver.resolve()) {
                    is CurrentLocationResult.Success -> {
                        val draftState = mutableState.value
                        val distanceMiles =
                            if (draftState.distanceTouched) {
                                draftState.selectedDistanceMiles
                            } else {
                                uiState.value.selectedDistanceMiles
                            }
                        val saveResult =
                            repository.saveLocation(
                                result.zipCode,
                                distanceMiles,
                            )
                        val message =
                            when (saveResult) {
                                ProfileMutationResult.Success -> "Current location saved to your profile."
                                ProfileMutationResult.InvalidZip -> "That location did not provide a valid ZIP code."
                                ProfileMutationResult.SyncFailed ->
                                    "LaughTrack could not save your current location. You can still enter a ZIP code."
                            }
                        val saved = saveResult == ProfileMutationResult.Success
                        mutableState.update {
                            it.copy(
                                isResolvingCurrentLocation = false,
                                message = message,
                                zipCodeDraftTouched = if (saved) false else it.zipCodeDraftTouched,
                                distanceTouched = if (saved) false else it.distanceTouched,
                            )
                        }
                    }
                    CurrentLocationResult.PermissionDenied -> {
                        finishLocationResolution(
                            "Location permission was denied. You can still enter a ZIP code.",
                        )
                    }
                    CurrentLocationResult.LocationUnavailable -> {
                        finishLocationResolution(
                            "Your current location is unavailable. You can still enter a ZIP code.",
                        )
                    }
                    CurrentLocationResult.GeocodingFailed -> {
                        finishLocationResolution(
                            "We could not find a ZIP code for your location. Try again or enter one manually.",
                        )
                    }
                }
            }
        }

        fun clearLocation() {
            mutate(resetLocationDrafts = true) {
                when (repository.clearLocation()) {
                    ProfileMutationResult.Success -> "Profile location cleared."
                    ProfileMutationResult.InvalidZip -> "Enter a valid 5-digit ZIP code."
                    ProfileMutationResult.SyncFailed -> "LaughTrack could not clear that profile location."
                }
            }
        }

        fun setEmailNotifications(enabled: Boolean) {
            mutate {
                when (repository.setEmailNotifications(enabled)) {
                    ProfileMutationResult.Success -> null
                    ProfileMutationResult.InvalidZip -> null
                    ProfileMutationResult.SyncFailed -> "LaughTrack could not save that alert preference."
                }
            }
        }

        fun setPushNotifications(enabled: Boolean) {
            mutate {
                when (repository.setPushNotifications(enabled)) {
                    ProfileMutationResult.Success -> null
                    ProfileMutationResult.InvalidZip -> null
                    ProfileMutationResult.SyncFailed -> "LaughTrack could not save that alert preference."
                }
            }
        }

        fun requestDeleteAccount() {
            mutableState.update { it.copy(showDeleteConfirmation = true) }
        }

        fun dismissDeleteAccount() {
            mutableState.update { it.copy(showDeleteConfirmation = false) }
        }

        fun requestSignOut() {
            mutableState.update { it.copy(showSignOutConfirmation = true) }
        }

        fun dismissSignOut() {
            mutableState.update { it.copy(showSignOutConfirmation = false) }
        }

        fun confirmSignOut() {
            viewModelScope.launch {
                mutableState.update {
                    it.copy(
                        isMutating = true,
                        message = null,
                        showSignOutConfirmation = false,
                    )
                }
                repository.signOut()
                // Clear the analytics identity so the next session isn't attributed to
                // the prior user (mirrors iOS reset() on sign-out).
                analytics.reset()
                mutableState.value = ProfileUiState(isLoading = false, message = "Signed out.")
            }
        }

        fun deleteAccount() {
            viewModelScope.launch {
                mutableState.update { it.copy(isMutating = true, message = null) }
                when (repository.deleteAccount()) {
                    ProfileMutationResult.Success -> {
                        analytics.reset()
                        mutableState.value = ProfileUiState(isLoading = false, message = "Account deleted.")
                    }
                    ProfileMutationResult.InvalidZip -> Unit
                    ProfileMutationResult.SyncFailed -> {
                        mutableState.update {
                            it.copy(
                                isMutating = false,
                                showDeleteConfirmation = false,
                                message = "Could not delete your account. Please try again.",
                            )
                        }
                    }
                }
            }
        }

        fun clearMessage() {
            mutableState.update { it.copy(message = null) }
        }

        private fun finishLocationResolution(message: String) {
            mutableState.update {
                it.copy(
                    isResolvingCurrentLocation = false,
                    message = message,
                )
            }
        }

        private fun mutate(
            resetLocationDrafts: Boolean = false,
            operation: suspend () -> String?,
        ) {
            viewModelScope.launch {
                mutableState.update { it.copy(isMutating = true, message = null) }
                val message = operation()
                mutableState.update {
                    it.copy(
                        isMutating = false,
                        message = message,
                        showDeleteConfirmation = false,
                        zipCodeDraftTouched = if (resetLocationDrafts) false else it.zipCodeDraftTouched,
                        distanceTouched = if (resetLocationDrafts) false else it.distanceTouched,
                    )
                }
            }
        }
    }
