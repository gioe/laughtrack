package app.laughtrack.android

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Build
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeFalse
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.util.concurrent.CopyOnWriteArrayList

/** Native permission coverage requires a fresh, denied permission prepared before instrumentation starts. */
@HiltAndroidTest
class NotificationPermissionTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Test
    fun explains_benefit_before_the_user_explicitly_enables_notifications() {
        var requests = 0
        showControl(NotificationPermissionAction.Request) { requests++ }

        composeRule.onNodeWithText("favorite comedians have shows nearby", substring = true).assertIsDisplayed()
        composeRule.onNodeWithText(
            "Your saved alert preference will stay the same.",
            substring = true,
        ).assertIsDisplayed()
        composeRule.onNodeWithText("Enable on this device").assertIsDisplayed().assertIsEnabled()
        composeRule.runOnIdle { assertEquals(0, requests) }

        composeRule.onNodeWithText("Enable on this device").performClick()
        composeRule.runOnIdle { assertEquals(1, requests) }
    }

    @Test
    fun denied_permission_offers_an_explicit_settings_recovery_action() {
        var settingsOpens = 0
        showControl(NotificationPermissionAction.Settings) { settingsOpens++ }

        composeRule.onNodeWithText("Push alerts are off on this device.", substring = true).assertIsDisplayed()
        composeRule.onNodeWithText("Enable on this device").assertDoesNotExist()
        composeRule.onNodeWithText("Open notification settings").assertIsDisplayed().assertIsEnabled()
        composeRule.runOnIdle { assertEquals(0, settingsOpens) }

        composeRule.onNodeWithText("Open notification settings").performClick()
        composeRule.runOnIdle { assertEquals(1, settingsOpens) }
    }

    @Test
    fun granted_permission_shows_status_without_another_enable_action() {
        var requests = 0
        showControl(NotificationPermissionAction.None) { requests++ }

        composeRule.onNodeWithText("Push alerts are allowed on this device.").assertIsDisplayed()
        composeRule.onNodeWithText("Enable on this device").assertDoesNotExist()
        composeRule.onNodeWithText("Open notification settings").assertDoesNotExist()
        composeRule.runOnIdle { assertEquals(0, requests) }
    }

    @Test
    fun pending_os_request_disables_repeat_taps() {
        var requests = 0
        showControl(NotificationPermissionAction.Request, requesting = true) { requests++ }

        composeRule.onNodeWithText("Enable on this device").assertIsDisplayed().assertIsNotEnabled().performClick()
        composeRule.runOnIdle { assertEquals(0, requests) }
    }

    @Test
    fun real_control_requests_only_after_tap_and_handles_native_denial_and_retry() {
        assumeTrue(Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
        val activity = composeRule.activity
        assumeTrue(
            ContextCompat.checkSelfPermission(activity, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED,
        )
        assumeFalse(
            activity.getSharedPreferences("notification-permission", Context.MODE_PRIVATE)
                .getBoolean("requested", false),
        )
        val results = CopyOnWriteArrayList<Boolean>()
        composeRule.setContent {
            LaughTrackTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Column(modifier = Modifier.padding(horizontal = 24.dp, vertical = 64.dp)) {
                        NotificationPermissionControl { results += it }
                    }
                }
            }
        }
        composeRule.onNodeWithText("favorite comedians have shows nearby", substring = true).assertIsDisplayed()
        composeRule.onNodeWithText("Enable on this device").assertIsEnabled()
        composeRule.runOnIdle { assertTrue(results.isEmpty()) }
        assertNull(permissionButton("permission_deny_button"))
        captureNative("before-request")

        composeRule.onNodeWithText("Enable on this device").performClick()
        awaitNative { permissionButton("permission_deny_button") != null }
        captureNative("system-prompt")
        assertTrue(permissionButton("permission_deny_button")!!.performAction(AccessibilityNodeInfo.ACTION_CLICK))
        awaitNative { results.size == 1 }
        composeRule.onNodeWithText("Push alerts are off on this device.", substring = true).assertIsDisplayed()
        assertEquals(listOf(false), results.toList())
        assertNull(permissionButton("permission_deny_button"))
        captureNative("after-denial")

        if (ActivityCompat.shouldShowRequestPermissionRationale(activity, Manifest.permission.POST_NOTIFICATIONS)) {
            composeRule.onNodeWithText("Enable on this device").assertIsEnabled().performClick()
            awaitNative { permissionButton("permission_allow_button") != null }
            assertTrue(permissionButton("permission_allow_button")!!.performAction(AccessibilityNodeInfo.ACTION_CLICK))
            awaitNative { results.size == 2 }
            composeRule.onNodeWithText("Push alerts are allowed on this device.").assertIsDisplayed()
            assertEquals(listOf(false, true), results.toList())
            composeRule.onNodeWithText("Enable on this device").assertDoesNotExist()
            captureNative("after-grant")
        } else {
            composeRule.onNodeWithText("Open notification settings").assertIsDisplayed().assertIsEnabled()
        }
    }

    private fun permissionButton(id: String): AccessibilityNodeInfo? =
        InstrumentationRegistry.getInstrumentation().uiAutomation.rootInActiveWindow
            ?.findAccessibilityNodeInfosByViewId("com.android.permissioncontroller:id/$id")
            ?.firstOrNull()

    private fun awaitNative(condition: () -> Boolean) {
        val deadline = SystemClock.elapsedRealtime() + 10_000L
        while (!condition() && SystemClock.elapsedRealtime() < deadline) {
            SystemClock.sleep(50L)
        }
        assertTrue("Native permission transition did not complete within 10 seconds", condition())
    }

    private fun captureNative(name: String) {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        // Accessibility updates precede the rendered frame, including native dialog animations.
        SystemClock.sleep(500L)
        val screenshot = checkNotNull(instrumentation.uiAutomation.takeScreenshot())
        val directory = File(instrumentation.targetContext.getExternalFilesDir(null), "notification-permission")
        directory.mkdirs()
        File(directory, "$name.png").outputStream().use { screenshot.compress(Bitmap.CompressFormat.PNG, 100, it) }
        screenshot.recycle()
    }

    private fun showControl(
        action: NotificationPermissionAction,
        requesting: Boolean = false,
        onEnable: () -> Unit,
    ) {
        composeRule.setContent {
            LaughTrackTheme {
                Column {
                    NotificationPermissionContent(action, requesting, onEnable)
                }
            }
        }
    }
}
