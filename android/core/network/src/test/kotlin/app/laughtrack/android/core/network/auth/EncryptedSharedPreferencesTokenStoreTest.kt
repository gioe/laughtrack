package app.laughtrack.android.core.network.auth

import android.content.SharedPreferences
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test
import java.security.GeneralSecurityException

class EncryptedSharedPreferencesTokenStoreTest {
    @Test
    fun constructionDoesNotBuildPrefsUntilFirstAccess() =
        runTest {
            var factoryCalls = 0
            val store =
                EncryptedSharedPreferencesTokenStore(
                    prefsFactory = {
                        factoryCalls++
                        FakeSharedPreferences()
                    },
                    clearCorruptedStorage = {},
                )

            // Lazy: constructing (Hilt injection) must not touch the Keystore/Tink.
            assertEquals(0, factoryCalls)

            store.read()

            // First access builds the prefs exactly once.
            assertEquals(1, factoryCalls)
        }

    @Test
    fun corruptedKeysetRecoversByClearingStorageInsteadOfCrashing() =
        runTest {
            var factoryCalls = 0
            var clearCalls = 0
            val store =
                EncryptedSharedPreferencesTokenStore(
                    prefsFactory = {
                        factoryCalls++
                        // First build throws as a corrupted alpha06 keyset would; the
                        // recreate after clearing succeeds.
                        if (factoryCalls == 1) {
                            throw GeneralSecurityException("corrupted keyset")
                        }
                        FakeSharedPreferences()
                    },
                    clearCorruptedStorage = { clearCalls++ },
                )

            // Does not throw: recovery deletes the corrupted store and rebuilds it.
            val tokens = store.read()

            assertNull(tokens) // fresh store -> user is signed out
            assertEquals(1, clearCalls)
            assertEquals(2, factoryCalls)
        }

    @Test
    fun corruptedKeysetRecoveryReportsForcedSignOutWithCause() =
        runTest {
            var factoryCalls = 0
            val cause = GeneralSecurityException("corrupted keyset")
            val recoveryEvents = mutableListOf<TokenStoreRecoveryEvent>()
            val store =
                EncryptedSharedPreferencesTokenStore(
                    prefsFactory = {
                        factoryCalls++
                        if (factoryCalls == 1) {
                            throw cause
                        }
                        FakeSharedPreferences()
                    },
                    clearCorruptedStorage = {},
                    onRecovery = recoveryEvents::add,
                )

            val tokens = store.read()

            assertNull(tokens)
            assertEquals(
                listOf(
                    TokenStoreRecoveryEvent(
                        cause = cause,
                        forcedSignOut = true,
                    ),
                ),
                recoveryEvents,
            )
        }

    @Test
    fun recreatedStoreRoundTripsTokensAfterRecovery() =
        runTest {
            var factoryCalls = 0
            val backing = FakeSharedPreferences()
            val store =
                EncryptedSharedPreferencesTokenStore(
                    prefsFactory = {
                        factoryCalls++
                        if (factoryCalls == 1) {
                            throw GeneralSecurityException("corrupted keyset")
                        }
                        backing
                    },
                    clearCorruptedStorage = {},
                )

            val saved =
                SessionTokens(
                    accessToken = "access",
                    refreshToken = "refresh",
                    expiresAtEpochSeconds = 1_700_000_000L,
                )
            store.save(saved)

            assertEquals(saved, store.read())
        }

    @Test
    fun unrecoverableKeystoreSurfacesInsteadOfBeingSilentlyMasked() {
        // If clearing storage cannot fix the corruption (e.g. the AndroidKeyStore
        // itself is unusable), the recreate throws again. There is no safe fallback
        // store, so the failure must surface rather than be silently swallowed into
        // a broken store. clearCorruptedStorage still runs exactly once.
        var clearCalls = 0
        val store =
            EncryptedSharedPreferencesTokenStore(
                prefsFactory = { throw GeneralSecurityException("keystore unusable") },
                clearCorruptedStorage = { clearCalls++ },
            )

        assertThrows(GeneralSecurityException::class.java) {
            runBlocking { store.read() }
        }
        assertEquals(1, clearCalls)
    }
}

/** Minimal in-memory [SharedPreferences] for unit tests (no Android runtime). */
private class FakeSharedPreferences : SharedPreferences {
    private val values = mutableMapOf<String, Any?>()

    override fun getAll(): MutableMap<String, *> = values

    override fun getString(
        key: String?,
        defValue: String?,
    ): String? = values[key] as? String ?: defValue

    override fun getStringSet(
        key: String?,
        defValues: MutableSet<String>?,
    ): MutableSet<String>? = defValues

    override fun getInt(
        key: String?,
        defValue: Int,
    ): Int = values[key] as? Int ?: defValue

    override fun getLong(
        key: String?,
        defValue: Long,
    ): Long = values[key] as? Long ?: defValue

    override fun getFloat(
        key: String?,
        defValue: Float,
    ): Float = values[key] as? Float ?: defValue

    override fun getBoolean(
        key: String?,
        defValue: Boolean,
    ): Boolean = values[key] as? Boolean ?: defValue

    override fun contains(key: String?): Boolean = values.containsKey(key)

    override fun edit(): SharedPreferences.Editor = FakeEditor(values)

    override fun registerOnSharedPreferenceChangeListener(
        listener: SharedPreferences.OnSharedPreferenceChangeListener?,
    ) = Unit

    override fun unregisterOnSharedPreferenceChangeListener(
        listener: SharedPreferences.OnSharedPreferenceChangeListener?,
    ) = Unit
}

private class FakeEditor(
    private val values: MutableMap<String, Any?>,
) : SharedPreferences.Editor {
    private val pending = mutableMapOf<String, Any?>()
    private val removed = mutableSetOf<String>()
    private var clearRequested = false

    override fun putString(
        key: String?,
        value: String?,
    ): SharedPreferences.Editor = also { pending[key!!] = value }

    override fun putStringSet(
        key: String?,
        values: MutableSet<String>?,
    ): SharedPreferences.Editor = also { pending[key!!] = values }

    override fun putInt(
        key: String?,
        value: Int,
    ): SharedPreferences.Editor = also { pending[key!!] = value }

    override fun putLong(
        key: String?,
        value: Long,
    ): SharedPreferences.Editor = also { pending[key!!] = value }

    override fun putFloat(
        key: String?,
        value: Float,
    ): SharedPreferences.Editor = also { pending[key!!] = value }

    override fun putBoolean(
        key: String?,
        value: Boolean,
    ): SharedPreferences.Editor = also { pending[key!!] = value }

    override fun remove(key: String?): SharedPreferences.Editor = also { removed += key!! }

    override fun clear(): SharedPreferences.Editor = also { clearRequested = true }

    override fun commit(): Boolean {
        applyChanges()
        return true
    }

    override fun apply() {
        applyChanges()
    }

    private fun applyChanges() {
        if (clearRequested) {
            values.clear()
        }
        removed.forEach { values.remove(it) }
        values.putAll(pending)
    }
}
