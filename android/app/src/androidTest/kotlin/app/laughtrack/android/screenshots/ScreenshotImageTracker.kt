package app.laughtrack.android.screenshots

import android.os.SystemClock
import coil.EventListener
import coil.request.ErrorResult
import coil.request.ImageRequest
import coil.request.SuccessResult
import java.util.Collections
import java.util.IdentityHashMap

/** Tracks Coil requests so screenshots never capture an in-flight decode. */
class ScreenshotImageTracker : EventListener {
    private val inFlight =
        Collections.synchronizedSet(
            Collections.newSetFromMap(IdentityHashMap<ImageRequest, Boolean>()),
        )

    override fun onStart(request: ImageRequest) {
        inFlight.add(request)
    }

    override fun onCancel(request: ImageRequest) {
        inFlight.remove(request)
    }

    override fun onError(
        request: ImageRequest,
        result: ErrorResult,
    ) {
        inFlight.remove(request)
    }

    override fun onSuccess(
        request: ImageRequest,
        result: SuccessResult,
    ) {
        inFlight.remove(request)
    }

    fun awaitIdle(timeoutMs: Long = 10_000) {
        val deadline = SystemClock.uptimeMillis() + timeoutMs
        while (inFlight.isNotEmpty() && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(20)
        }
        check(inFlight.isEmpty()) { "${inFlight.size} screenshot artwork request(s) still in flight" }
    }
}
