package app.laughtrack.android.core.data.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import androidx.core.content.ContextCompat
import app.laughtrack.android.core.data.runCatchingCancellable
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.util.Locale
import javax.inject.Inject
import kotlin.coroutines.resume

sealed interface CurrentLocationResult {
    data class Success(val zipCode: String) : CurrentLocationResult

    data object PermissionDenied : CurrentLocationResult

    data object LocationUnavailable : CurrentLocationResult

    data object GeocodingFailed : CurrentLocationResult
}

/** Resolves the device's current location into a five-digit US ZIP code. */
interface CurrentLocationResolver {
    suspend fun resolve(): CurrentLocationResult
}

class DeviceCurrentLocationResolver
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) : CurrentLocationResolver {
        private val client: FusedLocationProviderClient by lazy {
            LocationServices.getFusedLocationProviderClient(context)
        }

        @SuppressLint("MissingPermission")
        override suspend fun resolve(): CurrentLocationResult {
            if (!hasLocationPermission()) return CurrentLocationResult.PermissionDenied

            val location =
                suspendCancellableCoroutine<Location?> { continuation ->
                    client.lastLocation
                        .addOnSuccessListener { location ->
                            if (continuation.isActive) continuation.resume(location)
                        }.addOnFailureListener {
                            if (continuation.isActive) continuation.resume(null)
                        }.addOnCanceledListener {
                            if (continuation.isActive) continuation.resume(null)
                        }
                } ?: return CurrentLocationResult.LocationUnavailable

            val zipCode =
                runCatchingCancellable {
                    withContext(Dispatchers.IO) {
                        @Suppress("DEPRECATION")
                        Geocoder(context, Locale.US)
                            .getFromLocation(location.latitude, location.longitude, 1)
                            ?.firstOrNull()
                            ?.postalCode
                            ?.filter(Char::isDigit)
                            ?.take(5)
                            ?.takeIf { it.length == 5 }
                    }
                }.getOrNull()

            return zipCode?.let(CurrentLocationResult::Success)
                ?: CurrentLocationResult.GeocodingFailed
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
