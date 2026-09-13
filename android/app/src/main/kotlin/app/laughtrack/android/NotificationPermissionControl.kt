package app.laughtrack.android

import android.Manifest
import android.app.Activity
import android.app.NotificationManager
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import app.laughtrack.android.push.PushNotifications

@Composable
internal fun NotificationPermissionControl(onResult: (Boolean) -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val history = remember(context) { context.getSharedPreferences("notification-permission", Context.MODE_PRIVATE) }

    fun currentAction(): NotificationPermissionAction =
        notificationPermissionAction(
            supportsRuntimePermission = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU,
            permissionGranted =
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
                    PackageManager.PERMISSION_GRANTED,
            notificationsEnabled =
                NotificationManagerCompat.from(context).areNotificationsEnabled() &&
                    context.getSystemService(NotificationManager::class.java)
                        .getNotificationChannel(PushNotifications.CHANNEL_ID)?.importance !=
                    NotificationManager.IMPORTANCE_NONE,
            previouslyRequested = history.getBoolean("requested", false),
            shouldShowRationale =
                context.notificationActivity()?.let {
                    ActivityCompat.shouldShowRequestPermissionRationale(it, Manifest.permission.POST_NOTIFICATIONS)
                } == true,
        )
    var action by remember { mutableStateOf(currentAction()) }
    var requesting by remember { mutableStateOf(false) }
    val launcher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            requesting = false
            action = currentAction()
            onResult(granted)
        }
    DisposableEffect(lifecycle, context) {
        val observer =
            LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) action = currentAction()
            }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    NotificationPermissionContent(action, requesting) {
        when (action) {
            NotificationPermissionAction.Request -> {
                requesting = true
                history.edit().putBoolean("requested", true).apply()
                launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
            NotificationPermissionAction.Settings ->
                context.startActivity(
                    Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                        .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName),
                )
            NotificationPermissionAction.None -> Unit
        }
    }
}

@Composable
internal fun NotificationPermissionContent(
    action: NotificationPermissionAction,
    requesting: Boolean,
    onEnable: () -> Unit,
) {
    Text(
        text =
            if (action == NotificationPermissionAction.None) {
                "Push alerts are allowed on this device."
            } else {
                "Push alerts are off on this device. Allow notifications to hear when your favorite comedians " +
                    "have shows nearby. " +
                    "Your saved alert preference will stay the same."
            },
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    if (action != NotificationPermissionAction.None) {
        OutlinedButton(onClick = onEnable, enabled = !requesting) {
            Text(
                if (action == NotificationPermissionAction.Request) {
                    "Enable on this device"
                } else {
                    "Open notification settings"
                },
            )
        }
    }
}

private tailrec fun Context.notificationActivity(): Activity? =
    when (this) {
        is Activity -> this
        is ContextWrapper -> baseContext.notificationActivity()
        else -> null
    }
