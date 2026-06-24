package app.laughtrack.android.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.laughtrack.android.MainActivity
import app.laughtrack.android.R

/**
 * Notification channel + posting for comedian-arrival pushes. The tap PendingIntent
 * relaunches [MainActivity] with the `showId`/`url` extras that MainActivity already
 * routes through LaughTrackDeepLink.routeFromPush into a ShowDetail navigation.
 */
object PushNotifications {
    const val CHANNEL_ID = "comedian_arrivals"

    fun ensureChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Comedian arrivals",
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = "Alerts when a comedian you follow has a show near you."
        }
        context.getSystemService(NotificationManager::class.java)
            ?.createNotificationChannel(channel)
    }

    fun show(
        context: Context,
        title: String,
        body: String,
        showId: String?,
        url: String?,
    ) {
        ensureChannel(context)
        if (!hasPostPermission(context)) return

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            showId?.let { putExtra("showId", it) }
            url?.let { putExtra("url", it) }
        }
        // Distinct ids so unrelated pushes stack instead of replacing each other
        // under FLAG_UPDATE_CURRENT; comedian-arrival pushes always carry a showId.
        val notificationId = showId?.toIntOrNull() ?: (title + body).hashCode()
        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        NotificationManagerCompat.from(context).notify(notificationId, notification)
    }

    private fun hasPostPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
}
