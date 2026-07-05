package app.laughtrack.android.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

/**
 * FCM entry point: syncs refreshed tokens to the backend and turns incoming
 * comedian-arrival data messages into a tappable notification. Mirrors the iOS
 * APNs delivery path; the `showId`/`url` data keys match what the server sender
 * emits (apps/scraper notification service) and what MainActivity routes on.
 */
@AndroidEntryPoint
class LaughTrackMessagingService : FirebaseMessagingService() {
    @Inject
    lateinit var pushTokenManager: PushTokenManager

    override fun onNewToken(token: String) {
        // onNewToken runs on an FCM background thread; block so the POST completes
        // before the framework can tear the service down (no leaked service scope).
        runBlocking { pushTokenManager.register(token) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val appName = applicationInfo.loadLabel(packageManager).toString()
        val title = message.notification?.title ?: data["title"] ?: appName
        val body = message.notification?.body ?: data["body"].orEmpty()
        PushNotifications.show(
            context = this,
            title = title,
            body = body,
            showId = data["showId"],
            url = data["url"],
            imageUrl = data["imageUrl"],
            route = data["route"],
        )
    }
}
