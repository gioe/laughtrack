package app.laughtrack.android.core.data.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * App-wide trigger for the sign-in prompt shown when a signed-out user attempts a
 * gated action (currently: favoriting). A singleton so the data layer that detects
 * the gated attempt ([FavoritesRepository]) and the UI layer that presents the
 * prompt (AppShell's LoginPromptSheet) share one source of truth. Mirrors iOS
 * LoginModalPresenter.
 */
@Singleton
class LoginPromptController
    @Inject
    constructor() {
        private val _visible = MutableStateFlow(false)

        /** True while the sign-in prompt should be presented. */
        val visible: StateFlow<Boolean> = _visible.asStateFlow()

        /** Request the sign-in prompt (called when a guest hits a gated action). */
        fun request() {
            _visible.value = true
        }

        /** Dismiss the prompt (manual close, or after a successful sign-in). */
        fun dismiss() {
            _visible.value = false
        }
    }
