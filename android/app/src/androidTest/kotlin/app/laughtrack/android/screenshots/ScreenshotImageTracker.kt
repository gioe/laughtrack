package app.laughtrack.android.screenshots

import android.os.SystemClock
import coil.EventListener
import coil.request.ErrorResult
import coil.request.ImageRequest
import coil.request.SuccessResult
import java.util.concurrent.atomic.AtomicInteger

/** Tracks Coil requests so screenshots never capture an in-flight decode. */
class ScreenshotImageTracker : EventListener {
    private val inFlight = AtomicInteger(0)

    override fun onStart(request: ImageRequest) {
        inFlight.incrementAndGet()
    }

    override fun onCancel(request: ImageRequest) {
        inFlight.decrementAndGet()
    }

    override fun onError(
        request: ImageRequest,
        result: ErrorResult,
    ) {
        inFlight.decrementAndGet()
    }

    override fun onSuccess(
        request: ImageRequest,
        result: SuccessResult,
    ) {
        inFlight.decrementAndGet()
    }

    fun awaitIdle(timeoutMs: Long = 10_000) {
        val deadline = SystemClock.uptimeMillis() + timeoutMs
        while (inFlight.get() != 0 && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(20)
        }
        check(inFlight.get() == 0) { "${inFlight.get()} screenshot artwork request(s) still in flight" }
    }
}
