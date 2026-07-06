package app.laughtrack.android.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.laughtrack.android.MainActivity
import app.laughtrack.android.R
import java.net.HttpURLConnection
import java.net.URL

/**
 * Notification channel + posting for comedian-arrival pushes. The tap PendingIntent
 * relaunches [MainActivity] with the `showId`/`url` extras that MainActivity already
 * routes through LaughTrackDeepLink.routeFromPush into a ShowDetail navigation.
 */
object PushNotifications {
    const val CHANNEL_ID = "comedian_arrivals"

    fun ensureChannel(context: Context) {
        val channel =
            NotificationChannel(
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
        imageUrl: String? = null,
        route: String? = null,
        showIds: String? = null,
    ) {
        ensureChannel(context)
        if (!hasPostPermission(context)) return

        val intent =
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                showId?.let { putExtra("showId", it) }
                url?.let { putExtra("url", it) }
                // Grouped pushes set route so the tap opens the Favorites tab;
                // MainActivity routes it ahead of the showId fallback. showIds
                // scope that tab to the push's shows.
                route?.let { putExtra("route", it) }
                showIds?.let { putExtra("showIds", it) }
            }
        // Distinct ids so unrelated pushes stack instead of replacing each other
        // under FLAG_UPDATE_CURRENT; comedian-arrival pushes always carry a showId.
        val notificationId = showId?.toIntOrNull() ?: (title + body).hashCode()
        val pendingIntent =
            PendingIntent.getActivity(
                context,
                notificationId,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

        val builder =
            NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_stat_notification)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent)

        // Rich push: show the comedian headshot as the large icon collapsed and a
        // big picture when expanded. Falls back to BigText when there's no image
        // or the download fails.
        val headshot = imageUrl?.let(::loadBitmap)
        if (headshot != null) {
            builder
                .setLargeIcon(headshot)
                .setStyle(
                    NotificationCompat.BigPictureStyle()
                        .bigPicture(headshot)
                        .bigLargeIcon(null as Bitmap?),
                )
        } else {
            builder.setStyle(NotificationCompat.BigTextStyle().bigText(body))
        }

        NotificationManagerCompat.from(context).notify(notificationId, builder.build())
    }

    /**
     * Blocking fetch of a remote image into a Bitmap. Only called from
     * [LaughTrackMessagingService.onMessageReceived], which runs on an FCM
     * background thread, so a synchronous download is safe here. Returns null on
     * any failure so the notification still posts without the image.
     */
    private fun loadBitmap(imageUrl: String): Bitmap? =
        runCatching {
            val connection = (URL(imageUrl).openConnection() as HttpURLConnection).apply {
                connectTimeout = 5_000
                readTimeout = 5_000
                doInput = true
            }
            try {
                connection.inputStream.use { BitmapFactory.decodeStream(it) }
            } finally {
                connection.disconnect()
            }
        }.getOrNull()

    private fun hasPostPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
}
