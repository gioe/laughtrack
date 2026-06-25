package app.laughtrack.android.core.network.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class EncryptedSharedPreferencesTokenStore(
    context: Context,
) : TokenStore {
    private val prefs =
        EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build(),
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )

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
        const val PREFS_NAME = "laughtrack_session_tokens"
        const val KEY_ACCESS_TOKEN = "access_token"
        const val KEY_REFRESH_TOKEN = "refresh_token"
        const val KEY_EXPIRES_AT = "expires_at_epoch_seconds"
    }
}
