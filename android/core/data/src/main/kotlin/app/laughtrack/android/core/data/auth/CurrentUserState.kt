package app.laughtrack.android.core.data.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * App-wide snapshot of the signed-in user's roles, populated once from /me at
 * launch (MainActivity) and consumed by feature screens that gate admin-only UI —
 * currently the copyable Show-ID badge on Show Detail. A singleton so the badge
 * doesn't have to re-fetch /me on every show open. Resets on sign-out.
 */
@Singleton
class CurrentUserState
    @Inject
    constructor() {
        private val _isAdmin = MutableStateFlow(false)

        /** True when the signed-in user has the admin role (from /me `isAdmin`). */
        val isAdmin: StateFlow<Boolean> = _isAdmin.asStateFlow()

        fun setAdmin(isAdmin: Boolean) {
            _isAdmin.value = isAdmin
        }

        fun reset() {
            _isAdmin.value = false
        }
    }
