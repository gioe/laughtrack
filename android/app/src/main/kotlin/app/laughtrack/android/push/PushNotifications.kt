package app.laughtrack.android.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.drawable.BitmapDrawable
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.laughtrack.android.MainActivity
import app.laughtrack.android.R
import coil.imageLoader
import coil.request.ImageRequest
import coil.request.SuccessResult
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull

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

    /**
     * Fields from an incoming FCM data message that [show] renders into a
     * comedian-arrival notification. Grouped into one payload so [show] stays
     * under detekt's parameter-count threshold.
     */
    data class NotificationContent(
        val title: String,
        val body: String,
        val showId: String?,
        val url: String?,
        val imageUrl: String? = null,
        val route: String? = null,
        val showIds: String? = null,
    )

    fun show(
        context: Context,
        content: NotificationContent,
    ) {
        ensureChannel(context)
        if (!hasPostPermission(context)) return

        val title = content.title
        val body = content.body
        val intent =
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                content.showId?.let { putExtra("showId", it) }
                content.url?.let { putExtra("url", it) }
                // Grouped pushes set route so the tap opens the Favorites tab;
                // MainActivity routes it ahead of the showId fallback. showIds
                // scope that tab to the push's shows.
                content.route?.let { putExtra("route", it) }
                content.showIds?.let { putExtra("showIds", it) }
            }
        // Distinct ids so unrelated pushes stack instead of replacing each other
        // under FLAG_UPDATE_CURRENT; comedian-arrival pushes always carry a showId.
        val notificationId = content.showId?.toIntOrNull() ?: (title + body).hashCode()
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
        val headshot = content.imageUrl?.let { loadBitmap(context, it) }
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

    // BigPicture headshots come from the CDN at arbitrary resolutions; cap the
    // decode so a huge original can't OOM the process or overflow the binder
    // transaction that carries the notification (TransactionTooLargeException).
    private const val MAX_IMAGE_DIMENSION_PX = 1024

    // FCM's onMessageReceived budget is ~10s; give the image fetch half of it so
    // the notification still posts (BigText fallback) when the CDN is slow.
    private const val IMAGE_FETCH_TIMEOUT_MS = 5_000L

    /**
     * Blocking fetch of a remote image into a Bitmap via Coil's singleton
     * [coil.ImageLoader] (shared connection pool and memory/disk caches with
     * core:ui's RemoteImage). Only called from
     * [LaughTrackMessagingService.onMessageReceived], which runs on an FCM
     * background thread, so blocking here is safe. Returns null on any failure
     * or timeout so the notification still posts without the image.
     */
    private fun loadBitmap(
        context: Context,
        imageUrl: String,
    ): Bitmap? =
        runCatching {
            val request =
                ImageRequest.Builder(context)
                    .data(imageUrl)
                    .size(MAX_IMAGE_DIMENSION_PX)
                    // Notifications render through RemoteViews, which cannot
                    // draw hardware bitmaps.
                    .allowHardware(false)
                    .build()
            val result =
                runBlocking {
                    withTimeoutOrNull(IMAGE_FETCH_TIMEOUT_MS) {
                        context.imageLoader.execute(request)
                    }
                }
            ((result as? SuccessResult)?.drawable as? BitmapDrawable)?.bitmap
        }.getOrNull()

    private fun hasPostPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
}
