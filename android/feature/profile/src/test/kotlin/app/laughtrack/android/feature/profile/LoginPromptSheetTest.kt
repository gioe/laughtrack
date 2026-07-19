package app.laughtrack.android.feature.profile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LoginPromptSheetTest {
    @Test
    fun `Google is first and is the only primary option`() {
        assertEquals(LoginPromptProvider.Google, loginPromptOptions.first().provider)
        assertTrue(loginPromptOptions.first().isPrimary)
        assertEquals(1, loginPromptOptions.count { it.isPrimary })
    }

    @Test
    fun `Apple and email remain visible alternatives in order`() {
        assertEquals(
            listOf(LoginPromptProvider.Apple, LoginPromptProvider.Email),
            loginPromptOptions.filterNot { it.isPrimary }.map { it.provider },
        )
        assertEquals(
            listOf("Continue with Apple", "Email me a sign-in link"),
            loginPromptOptions.filterNot { it.isPrimary }.map { it.label },
        )
        assertFalse(loginPromptOptions.drop(1).any { it.isPrimary })
        assertEquals(loginPromptOptions.size, loginPromptOptions.map { it.label }.distinct().size)
        assertFalse(loginPromptOptions.any { it.label == "Not now" })
    }
}
