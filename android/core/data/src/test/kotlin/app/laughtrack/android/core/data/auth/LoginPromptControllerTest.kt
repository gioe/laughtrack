package app.laughtrack.android.core.data.auth

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LoginPromptControllerTest {
    @Test
    fun starts_hidden() {
        assertFalse(LoginPromptController().visible.value)
    }

    @Test
    fun request_shows_then_dismiss_hides() {
        val controller = LoginPromptController()

        controller.request()
        assertTrue(controller.visible.value)

        controller.dismiss()
        assertFalse(controller.visible.value)
    }
}
