package app.laughtrack.android.core.data.location

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** The area the Home feed is scoped to: an explicit or hero-inferred ZIP plus radius. */
data class HomeLocation(
    val zip: String,
    val distanceMiles: Int,
)

/**
 * App-wide snapshot of the Home feed's active location, published by
 * HomeViewModel on every feed state and consumed by SearchViewModel to seed its
 * geo pivots — so Search opens scoped to the same area Home is showing, the way
 * iOS seeds SearchRootModel from the nearby preference. Null until the Home
 * feed has a location (or when the server could not infer one). A singleton
 * because the two feature ViewModels must observe the same instance
 * (CurrentUserState pattern).
 */
@Singleton
class HomeLocationState
    @Inject
    constructor() {
        private val _location = MutableStateFlow<HomeLocation?>(null)
        val location: StateFlow<HomeLocation?> = _location.asStateFlow()

        /** Publish the Home feed's current area; a null [zip] clears it. */
        fun update(
            zip: String?,
            distanceMiles: Int,
        ) {
            _location.value = zip?.let { HomeLocation(it, distanceMiles) }
        }
    }
