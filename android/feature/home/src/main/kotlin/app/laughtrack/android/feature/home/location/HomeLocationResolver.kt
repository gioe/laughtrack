package app.laughtrack.android.feature.home.location

import app.laughtrack.android.core.data.location.CurrentLocationResolver
import app.laughtrack.android.core.data.location.CurrentLocationResult
import javax.inject.Inject

/** Resolves the device's current location to a 5-digit US ZIP, or null. */
interface HomeLocationResolver {
    suspend fun resolveZip(): String?
}

/**
 * Compatibility adapter for Home's nullable resolver contract. The shared core
 * resolver retains structured failures for callers such as Profile, while Home
 * preserves its existing silent fallback behavior.
 */
class DeviceHomeLocationResolver
    @Inject
    constructor(
        private val resolver: CurrentLocationResolver,
    ) : HomeLocationResolver {
        override suspend fun resolveZip(): String? = (resolver.resolve() as? CurrentLocationResult.Success)?.zipCode
    }
