package app.laughtrack.android

import org.junit.Assert.assertEquals
import org.junit.Test

class NotificationPermissionPolicyTest {
    @Test fun grantedPermissionNeedsNoPrompt() {
        assertEquals(NotificationPermissionAction.None, notificationPermissionAction(true, true, true, true, false))
    }

    @Test fun firstExplicitActionCanRequestPermission() {
        assertEquals(
            NotificationPermissionAction.Request,
            notificationPermissionAction(true, false, false, false, false),
        )
    }

    @Test fun denialAllowsOnlyAnExplicitRetryWhenAndroidAllowsIt() {
        assertEquals(NotificationPermissionAction.Request, notificationPermissionAction(true, false, false, true, true))
    }

    @Test fun repeatedDenialOffersSettingsInsteadOfAnotherOsPrompt() {
        repeat(3) {
            assertEquals(
                NotificationPermissionAction.Settings,
                notificationPermissionAction(true, false, false, true, false),
            )
        }
    }

    @Test fun unsupportedOsNeverRequestsRuntimePermission() {
        assertEquals(NotificationPermissionAction.None, notificationPermissionAction(false, false, true, false, false))
        assertEquals(
            NotificationPermissionAction.Settings,
            notificationPermissionAction(false, false, false, false, false),
        )
    }

    @Test fun blockedChannelWithPermissionGrantedOffersSettings() {
        assertEquals(
            NotificationPermissionAction.Settings,
            notificationPermissionAction(true, true, false, true, false),
        )
    }
}
