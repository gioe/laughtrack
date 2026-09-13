package app.laughtrack.android

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.navigation.NavDestination
import androidx.navigation.NavDestination.Companion.hasRoute
import app.laughtrack.android.core.navigation.AppRoute
import kotlin.reflect.KClass

internal enum class AppShellMotionKind { TAB, DETAIL, PLAYER }

/** Native NavHost owns interruption, predictive-back progress, and system duration scaling. */
internal object AppShellMotion {
    const val TAB_DURATION_MS = 140
    const val DETAIL_DURATION_MS = 260

    fun kind(
        from: KClass<out AppRoute>,
        to: KClass<out AppRoute>,
    ): AppShellMotionKind =
        when {
            from == AppRoute.NowPlaying::class || to == AppRoute.NowPlaying::class -> AppShellMotionKind.PLAYER
            from in AppShellChrome.bottomBarRoutes && to in AppShellChrome.bottomBarRoutes -> AppShellMotionKind.TAB
            else -> AppShellMotionKind.DETAIL
        }

    private fun kind(
        from: NavDestination,
        to: NavDestination,
    ): AppShellMotionKind =
        when {
            from.hasRoute<AppRoute.NowPlaying>() || to.hasRoute<AppRoute.NowPlaying>() -> AppShellMotionKind.PLAYER
            AppShellChrome.showsBottomBar(from) && AppShellChrome.showsBottomBar(to) -> AppShellMotionKind.TAB
            else -> AppShellMotionKind.DETAIL
        }

    fun enter(
        from: NavDestination,
        to: NavDestination,
        popping: Boolean = false,
        forwardSign: Int = 1,
    ): EnterTransition =
        when (kind(from, to)) {
            AppShellMotionKind.TAB -> fadeIn(tween(TAB_DURATION_MS))
            AppShellMotionKind.PLAYER ->
                if (to.hasRoute<AppRoute.NowPlaying>()) {
                    slideInVertically(tween(DETAIL_DURATION_MS, easing = FastOutSlowInEasing)) { it }
                } else {
                    fadeIn(tween(DETAIL_DURATION_MS))
                }
            AppShellMotionKind.DETAIL ->
                fadeIn(tween(DETAIL_DURATION_MS)) +
                    slideInHorizontally(tween(DETAIL_DURATION_MS, easing = FastOutSlowInEasing)) {
                        (it * (if (popping) -0.04f else 0.12f) * forwardSign).toInt()
                    }
        }

    fun exit(
        from: NavDestination,
        to: NavDestination,
        popping: Boolean = false,
        forwardSign: Int = 1,
    ): ExitTransition =
        when (kind(from, to)) {
            AppShellMotionKind.TAB -> fadeOut(tween(TAB_DURATION_MS))
            AppShellMotionKind.PLAYER ->
                if (from.hasRoute<AppRoute.NowPlaying>()) {
                    slideOutVertically(tween(DETAIL_DURATION_MS, easing = FastOutSlowInEasing)) { it }
                } else {
                    fadeOut(tween(DETAIL_DURATION_MS))
                }
            AppShellMotionKind.DETAIL ->
                fadeOut(tween(DETAIL_DURATION_MS)) +
                    slideOutHorizontally(tween(DETAIL_DURATION_MS, easing = FastOutSlowInEasing)) {
                        (it * (if (popping) 0.12f else -0.04f) * forwardSign).toInt()
                    }
        }
}
