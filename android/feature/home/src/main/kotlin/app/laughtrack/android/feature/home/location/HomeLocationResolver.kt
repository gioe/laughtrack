package app.laughtrack.android.feature.home.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.util.Locale
import javax.inject.Inject
import kotlin.coroutines.resume

/** Resolves the device's current location to a 5-digit US ZIP, or null. */
interface HomeLocationResolver {
    suspend fun resolveZip(): String?
}

/**
 * Device-backed resolver: reads the last known location via FusedLocationProvider
 * and reverse-geocodes it to a postal code. Returns null when location permission
 * is not granted, no location is available, or geocoding fails — the caller keeps
 * the manual-ZIP path in that case. Mirrors the iOS HomeView "Use location" flow.
 */
class DeviceHomeLocationResolver
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) : HomeLocationResolver {
        private val client: FusedLocationProviderClient by lazy {
            LocationServices.getFusedLocationProviderClient(context)
        }

        @SuppressLint("MissingPermission")
        override suspend fun resolveZip(): String? {
            if (!hasLocationPermission()) return null
            val location =
                suspendCancellableCoroutine<Location?> { continuation ->
                    client.lastLocation
                        .addOnSuccessListener { continuation.resume(it) }
                        .addOnFailureListener { continuation.resume(null) }
                } ?: return null

            return withContext(Dispatchers.IO) {
                @Suppress("DEPRECATION")
                Geocoder(context, Locale.US)
                    .getFromLocation(location.latitude, location.longitude, 1)
                    ?.firstOrNull()
                    ?.postalCode
                    ?.take(5)
                    ?.takeIf { it.all(Char::isDigit) }
            }
        }

        private fun hasLocationPermission(): Boolean =
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            ) == PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                ) == PackageManager.PERMISSION_GRANTED
    }
