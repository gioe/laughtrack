package app.laughtrack.android.core.data

import kotlinx.coroutines.CancellationException

/**
 * Like [runCatching], but preserves structured coroutine cancellation.
 *
 * Lives in :core:data (not :core:ui) because it is a data-layer helper: the
 * feature repositories use it to wrap suspending network/DB calls. Keeping it
 * out of :core:ui is what lets the design-system module avoid a data-layer edge.
 *
 * The broad Throwable catch is the whole point of this helper (hence the
 * TooGenericExceptionCaught suppression): it mirrors stdlib runCatching, which
 * also catches Throwable, while rethrowing CancellationException first so
 * structured cancellation still propagates. Narrowing it would silently change
 * every repository call site's contract.
 */
@Suppress("TooGenericExceptionCaught")
suspend inline fun <T> runCatchingCancellable(crossinline block: suspend () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (error: CancellationException) {
        throw error
    } catch (error: Throwable) {
        Result.failure(error)
    }
