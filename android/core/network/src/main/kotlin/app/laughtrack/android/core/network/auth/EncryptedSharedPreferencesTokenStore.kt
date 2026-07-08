package app.laughtrack.android.core.network.auth

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.security.KeyStore

data class TokenStoreRecoveryEvent(
    val cause: Throwable,
    val forcedSignOut: Boolean,
)

/**
 * Token store backed by [EncryptedSharedPreferences].
 *
 * Two hardening measures guard against the Tink keyset-corruption crash loop that
 * the deprecated `androidx.security-crypto` 1.1.0-alpha06 is prone to:
 *
 *  1. **Lazy initialization** — [EncryptedSharedPreferences]/[MasterKey] construction
 *     does Keystore + Tink work that can throw. Doing it eagerly in the constructor
 *     runs it on the main thread at Hilt injection time, so a corrupted keyset crashes
 *     the app before anything can catch it. Here the prefs are built lazily on first
 *     access, which always happens inside `withContext(Dispatchers.IO)` below.
 *  2. **Corruption recovery** — if building the prefs throws (a corrupted keyset surfaces
 *     as `GeneralSecurityException` / `IOException` / `IllegalStateException` depending on
 *     the failure), the corrupted storage is deleted and the prefs are rebuilt with a
 *     fresh keyset. This signs the user out instead of crash-looping on every launch.
 *
 * The [prefsFactory]/[clearCorruptedStorage] seams exist so the recovery path can be
 * unit-tested without a real Android Keystore; production callers use the primary
 * constructor, which wires the real [EncryptedSharedPreferences] factory.
 */
class EncryptedSharedPreferencesTokenStore internal constructor(
    private val prefsFactory: () -> SharedPreferences,
    private val clearCorruptedStorage: () -> Unit,
    private val onRecovery: (TokenStoreRecoveryEvent) -> Unit = {},
) : TokenStore {
    constructor(context: Context) : this(
        prefsFactory = { createEncryptedPrefs(context) },
        clearCorruptedStorage = { deleteEncryptedPrefs(context) },
        onRecovery = { event ->
            Log.w(
                TAG,
                "Recovered from encrypted token-store corruption; forcedSignOut=${event.forcedSignOut}",
                event.cause,
            )
        },
    )

    // Built lazily so no Keystore/Tink work happens at Hilt injection time; the first
    // access below always runs on Dispatchers.IO. `lazy` defaults to thread-safe
    // (SYNCHRONIZED) initialization.
    private val prefs: SharedPreferences by lazy { openOrRecover() }

    // A corrupted alpha06 Tink keyset surfaces as several unrelated exception types
    // (GeneralSecurityException, IOException, and runtime IllegalState/IllegalArgument
    // from Tink), so the catch is intentionally broad. Narrowing the catch would
    // risk re-introducing the crash loop for a variant we did not enumerate.
    @Suppress("TooGenericExceptionCaught", "SwallowedException")
    private fun openOrRecover(): SharedPreferences =
        try {
            prefsFactory()
        } catch (e: Exception) {
            // Delete the encrypted prefs so a fresh keyset is generated on the retry —
            // the user is signed out rather than trapped in a permanent launch-time
            // crash loop.
            runCatching {
                onRecovery(
                    TokenStoreRecoveryEvent(
                        cause = e,
                        forcedSignOut = true,
                    ),
                )
            }
            clearCorruptedStorage()
            prefsFactory()
        }

    override suspend fun read(): SessionTokens? =
        withContext(Dispatchers.IO) {
            val accessToken = prefs.getString(KEY_ACCESS_TOKEN, null)
            val refreshToken = prefs.getString(KEY_REFRESH_TOKEN, null)
            val expiresAt = prefs.getLong(KEY_EXPIRES_AT, 0L)
            if (accessToken.isNullOrBlank() || refreshToken.isNullOrBlank() || expiresAt <= 0L) {
                null
            } else {
                SessionTokens(
                    accessToken = accessToken,
                    refreshToken = refreshToken,
                    expiresAtEpochSeconds = expiresAt,
                )
            }
        }

    override suspend fun save(tokens: SessionTokens) {
        withContext(Dispatchers.IO) {
            prefs.edit()
                .putString(KEY_ACCESS_TOKEN, tokens.accessToken)
                .putString(KEY_REFRESH_TOKEN, tokens.refreshToken)
                .putLong(KEY_EXPIRES_AT, tokens.expiresAtEpochSeconds)
                .apply()
        }
    }

    override suspend fun clear() {
        withContext(Dispatchers.IO) {
            prefs.edit().clear().apply()
        }
    }

    private companion object {
        const val KEY_ACCESS_TOKEN = "access_token"
        const val KEY_REFRESH_TOKEN = "refresh_token"
        const val KEY_EXPIRES_AT = "expires_at_epoch_seconds"
        const val TAG = "TokenStore"
    }
}

private const val PREFS_NAME = "laughtrack_session_tokens"

private fun createEncryptedPrefs(context: Context): SharedPreferences =
    EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

private fun deleteEncryptedPrefs(context: Context) {
    context.deleteSharedPreferences(PREFS_NAME)
    // The prefs file holds the Tink data keyset, but the wrapping key lives in the
    // AndroidKeyStore. If the MasterKey itself is the corrupt component, deleting
    // only the prefs file leaves the recreate throwing the same exception and the
    // crash loop intact. Drop the MasterKey alias too so a fresh key is generated.
    // Best-effort: a failure to delete the alias must not abort recovery.
    runCatching {
        KeyStore.getInstance(ANDROID_KEYSTORE)
            .apply { load(null) }
            .deleteEntry(MasterKey.DEFAULT_MASTER_KEY_ALIAS)
    }
}

private const val ANDROID_KEYSTORE = "AndroidKeyStore"
