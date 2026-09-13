package app.laughtrack.android

/** Describes an explicit settings action; evaluating this policy never launches a prompt. */
internal enum class NotificationPermissionAction { None, Request, Settings }

internal fun notificationPermissionAction(
    supportsRuntimePermission: Boolean,
    permissionGranted: Boolean,
    notificationsEnabled: Boolean,
    previouslyRequested: Boolean,
    shouldShowRationale: Boolean,
): NotificationPermissionAction =
    when {
        supportsRuntimePermission && !permissionGranted ->
            if (!previouslyRequested || shouldShowRationale) {
                NotificationPermissionAction.Request
            } else {
                NotificationPermissionAction.Settings
            }
        !notificationsEnabled -> NotificationPermissionAction.Settings
        else -> NotificationPermissionAction.None
    }
