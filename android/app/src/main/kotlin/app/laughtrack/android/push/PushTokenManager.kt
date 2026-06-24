package app.laughtrack.android.push

import android.content.Context
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Registers/deactivates this device's FCM token with the backend, mirroring iOS
 * PushDeviceTokenManager: POST /me/push-tokens to register, DELETE on sign-out.
 * The token is cached locally so sign-out can deactivate it even if the live FCM
 * token is unavailable. Every Firebase call is guarded — when no Firebase project
 * is configured (no google-services.json), the manager no-ops instead of crashing.
 */
@Singleton
class PushTokenManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val pushTokenApi: PushTokenApi,
) {
    private val prefs by lazy {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    /** Resolve the current FCM token (if Firebase is configured) and sync it. */
    suspend fun syncCurrentToken() {
        val token = currentFcmToken() ?: return
        register(token)
    }

    /** Sync a freshly issued token (from FirebaseMessagingService.onNewToken). */
    suspend fun register(token: String) {
        if (token.isBlank()) return
        val ok = runCatching { pushTokenApi.register(PushTokenRequest(token = token)) }
            .getOrNull()
            ?.isSuccessful == true
        if (ok) prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    /** Deactivate the cached token server-side on sign-out, then forget it locally. */
    suspend fun deactivateCurrentToken() {
        val token = prefs.getString(KEY_TOKEN, null) ?: return
        // Sign-out must proceed even if the server is unreachable (matches iOS).
        runCatching { pushTokenApi.deactivate(PushTokenRequest(token = token)) }
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    private suspend fun currentFcmToken(): String? =
        runCatching {
            suspendCancellableCoroutine<String?> { continuation ->
                FirebaseMessaging.getInstance().token
                    .addOnSuccessListener { token -> continuation.resume(token) }
                    .addOnFailureListener { continuation.resume(null) }
            }
        }.getOrNull()

    private companion object {
        const val PREFS_NAME = "laughtrack.push"
        const val KEY_TOKEN = "current-device-token"
    }
}
