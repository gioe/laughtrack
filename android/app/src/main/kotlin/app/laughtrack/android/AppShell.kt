package app.laughtrack.android

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavController
import androidx.navigation.NavDestination
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.AppTab
import app.laughtrack.android.core.playback.NowPlayingScreen
import app.laughtrack.android.core.playback.PodcastMiniPlayer
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.feature.detail.ui.ClubDetailScreen
import app.laughtrack.android.feature.detail.ui.ComedianDetailScreen
import app.laughtrack.android.feature.detail.ui.PodcastDetailScreen
import app.laughtrack.android.feature.detail.ui.ShowDetailScreen
import app.laughtrack.android.feature.home.HomeScreen
import app.laughtrack.android.feature.library.LibraryScreen
import app.laughtrack.android.feature.notifications.NotificationCenterScreen
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingScreen
import app.laughtrack.android.feature.profile.LoginPromptSheet
import app.laughtrack.android.feature.profile.ProfileScreen
import app.laughtrack.android.feature.search.ui.SearchScreen
import app.laughtrack.android.screenshots.AuthenticatedScreenshotPersona
import kotlin.reflect.KClass

/**
 * Root app shell: a three-tab bottom bar (Discover/Search/Favorites) over a typed
 * Navigation-Compose [NavHost]. Detail routes push onto the active tab's back
 * stack with cycle-dedup (see [openEntity]); Profile and Notification Center are
 * reached from the profile menu, not tabs — mirroring the iOS AppShellView.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppShell(
    navController: NavHostController = rememberNavController(),
    pendingRoute: AppRoute? = null,
    onRouteConsumed: () -> Unit = {},
    signedIn: Boolean = false,
    hasFavorites: Boolean = false,
    playbackController: PodcastPlaybackController? = null,
    showLoginPrompt: Boolean = false,
    onLoginPromptDismiss: () -> Unit = {},
    screenshotPersona: AuthenticatedScreenshotPersona? = null,
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination
    val showFavoritesTab = AppShellTabs.showsFavoritesTab(signedIn, hasFavorites)

    // Route a deep link / push target once it is delivered, then clear it so a
    // recomposition or config change doesn't re-navigate.
    LaunchedEffect(pendingRoute) {
        pendingRoute?.let {
            navController.openEntity(it)
            onRouteConsumed()
        }
    }

    // If the Favorites tab disappears (sign-out, or the user removes their last
    // favorite) while it is the active destination, fall back to Discover so the
    // user isn't stranded on a tab with no bottom-bar entry. Mirrors iOS
    // AppShellView's onChange(of: showFavoritesTab) reset to nearMe.
    LaunchedEffect(showFavoritesTab) {
        if (!showFavoritesTab &&
            currentDestination?.hierarchy?.any { it.hasRoute(AppRoute.Favorites::class) } == true
        ) {
            navController.switchTab(AppTab.DISCOVER)
        }
    }

    Scaffold(
        // TopAppBar/NavigationBar and detail heroes own their respective safe-area
        // padding. Reserving safeDrawing here as well leaves an opaque status-bar
        // strip above detail artwork instead of allowing true edge-to-edge chrome.
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = {
            if (AppShellChrome.showsTopAppBar(currentDestination)) {
                TopAppBar(
                    title = { Text("LaughTrack") },
                    actions = { ProfileMenu(navController) },
                )
            }
        },
        bottomBar = {
            if (AppShellChrome.showsBottomBar(currentDestination)) {
                NavigationBar {
                    AppShellTabs.visibleTabs(signedIn, hasFavorites).forEach { tab ->
                        val selected =
                            currentDestination?.hierarchy?.any {
                                it.hasRoute(tab.rootRoute::class)
                            } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = { navController.switchTab(tab) },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            NavHost(
                navController = navController,
                startDestination = AppRoute.Discover,
                modifier = Modifier.fillMaxSize(),
            ) {
                composable<AppRoute.Discover> {
                    HomeScreen(onOpenEntity = navController::openEntity)
                }
                composable<AppRoute.Search> {
                    SearchScreen(onOpenEntity = navController::openEntity)
                }
                composable<AppRoute.Favorites> { entry ->
                    val scopedShowIds = entry.toRoute<AppRoute.Favorites>().showIds
                    if (screenshotPersona == null) {
                        LibraryScreen(
                            signedIn = signedIn,
                            scopedShowIds = scopedShowIds,
                            onOpenProfile = { navController.openEntity(AppRoute.Profile) },
                        )
                    } else {
                        LibraryScreen(
                            signedIn = true,
                            scopedShowIds = scopedShowIds,
                            onOpenProfile = { navController.openEntity(AppRoute.Profile) },
                            snapshotOverride = screenshotPersona.favoritesSnapshot,
                        )
                    }
                }
                composable<AppRoute.ComedianOnboarding> {
                    ComedianOnboardingScreen(
                        onComplete = {
                            navController.navigate(AppRoute.Discover) {
                                popUpTo(AppRoute.ComedianOnboarding) { inclusive = true }
                                launchSingleTop = true
                            }
                        },
                    )
                }

                composable<AppRoute.ShowDetail> { entry ->
                    ShowDetailScreen(
                        id = entry.toRoute<AppRoute.ShowDetail>().id,
                        onBack = { navController.popBackStack() },
                        onHome = {
                            navController.navigate(AppRoute.Discover) {
                                popUpTo(AppRoute.Discover) { inclusive = false }
                                launchSingleTop = true
                            }
                        },
                        onOpenEntity = navController::openEntity,
                    )
                }
                composable<AppRoute.ComedianDetail> { entry ->
                    ComedianDetailScreen(
                        id = entry.toRoute<AppRoute.ComedianDetail>().id,
                        onBack = { navController.popBackStack() },
                        onOpenEntity = navController::openEntity,
                    )
                }
                composable<AppRoute.ClubDetail> { entry ->
                    ClubDetailScreen(
                        id = entry.toRoute<AppRoute.ClubDetail>().id,
                        onBack = { navController.popBackStack() },
                        onOpenEntity = navController::openEntity,
                    )
                }
                composable<AppRoute.PodcastDetail> { entry ->
                    PodcastDetailScreen(
                        id = entry.toRoute<AppRoute.PodcastDetail>().id,
                        onBack = { navController.popBackStack() },
                        onOpenEntity = navController::openEntity,
                    )
                }
                composable<AppRoute.NowPlaying> {
                    if (playbackController != null) {
                        NowPlayingScreen(playbackController = playbackController)
                    } else {
                        PlaceholderScreen("Now Playing")
                    }
                }

                composable<AppRoute.Profile> {
                    if (screenshotPersona == null) {
                        ProfileScreen()
                    } else {
                        ProfileScreen(stateOverride = screenshotPersona.profileUiState)
                    }
                }
                composable<AppRoute.NotificationCenter> {
                    if (screenshotPersona == null) {
                        NotificationCenterScreen(
                            onOpenEntity = navController::openEntity,
                            onBack = { navController.popBackStack() },
                        )
                    } else {
                        NotificationCenterScreen(
                            onOpenEntity = navController::openEntity,
                            onBack = { navController.popBackStack() },
                            dataOverride = screenshotPersona.notificationListResponseData,
                            referenceTime = screenshotPersona.notificationReferenceTime,
                        )
                    }
                }
            }

            if (playbackController != null) {
                PodcastMiniPlayer(
                    playbackController = playbackController,
                    onExpand = { navController.openEntity(AppRoute.NowPlaying) },
                    modifier = Modifier.align(Alignment.BottomCenter),
                )
            }
        }
    }

    // Sign-in prompt for gated actions (a guest tapping favorite). Overlays the
    // whole shell so it appears regardless of the active destination. Mirrors iOS
    // ContentView's login-modal sheet.
    if (showLoginPrompt) {
        LoginPromptSheet(onDismiss = onLoginPromptDismiss)
    }
}

@Composable
private fun ProfileMenu(navController: NavController) {
    var expanded by remember { mutableStateOf(false) }
    IconButton(onClick = { expanded = true }) {
        Icon(Icons.Filled.Person, contentDescription = "Profile menu")
    }
    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
        DropdownMenuItem(
            text = { Text("Profile") },
            onClick = {
                expanded = false
                navController.openEntity(AppRoute.Profile)
            },
        )
        DropdownMenuItem(
            text = { Text("Notifications") },
            onClick = {
                expanded = false
                navController.openEntity(AppRoute.NotificationCenter)
            },
        )
    }
}

private val AppTab.icon: ImageVector
    get() =
        when (this) {
            AppTab.DISCOVER -> Icons.Filled.Home
            AppTab.SEARCH -> Icons.Filled.Search
            AppTab.FAVORITES -> Icons.Filled.Favorite
        }

/**
 * Switch bottom-nav tabs: pop to the graph start (saving each tab's state),
 * single-top, and restore the target tab's saved state — the standard Compose
 * bottom-navigation pattern.
 */
fun NavController.switchTab(tab: AppTab) {
    navigate(tab.rootRoute) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}

/**
 * Open an entity detail (or Profile/Notifications) with cycle-dedup: if the route
 * is already on the back stack, pop back to it instead of pushing a duplicate.
 * Implements the contract specified and unit-tested by
 * `core:navigation` NavStackDedup.navigate.
 *
 * `popBackStack(route, inclusive=false)` pops to the NEAREST matching entry while
 * the spec's `indexOf` targets the FIRST — these diverge only if the same route
 * appeared twice on the stack, which this very dedup prevents from ever happening,
 * so the two stay equivalent in practice.
 */
fun NavController.openEntity(route: AppRoute) {
    if (!popBackStack(route, inclusive = false)) {
        navigate(route)
    }
}

internal object AppShellTabs {
    /**
     * Whether the Favorites bottom tab is exposed. Mirrors iOS
     * `AppShellView.showFavoritesTab`: only a signed-in user who has at least one
     * favorite (comedian) sees the tab — it is hidden for logged-out users and for
     * signed-in users with an empty favorites library.
     */
    fun showsFavoritesTab(
        signedIn: Boolean,
        hasFavorites: Boolean,
    ): Boolean = signedIn && hasFavorites

    /** Bottom-nav tabs in order, dropping Favorites when it should not be shown. */
    fun visibleTabs(
        signedIn: Boolean,
        hasFavorites: Boolean,
    ): List<AppTab> =
        AppTab.entries.filter {
            it != AppTab.FAVORITES || showsFavoritesTab(signedIn, hasFavorites)
        }
}

internal object AppShellChrome {
    /**
     * Canonical chrome membership per route class — the single source the
     * shipping predicates below read. Every [AppRoute] class must appear in
     * at least one of these three sets ([fullScreenRoutes] = neither bar);
     * AppShellChromeTest fails on any unclassified route.
     */
    val topAppBarRoutes: Set<KClass<out AppRoute>> =
        setOf(
            AppRoute.Favorites::class,
            AppRoute.ComedianOnboarding::class,
            AppRoute.NowPlaying::class,
            AppRoute.Profile::class,
        )

    /** Root-tab routes that keep the bottom navigation bar visible. */
    val bottomBarRoutes: Set<KClass<out AppRoute>> =
        setOf(
            AppRoute.Discover::class,
            AppRoute.Search::class,
            AppRoute.Favorites::class,
        )

    /** Routes that own their whole screen and render no shell bar at all. */
    val fullScreenRoutes: Set<KClass<out AppRoute>> =
        setOf(
            AppRoute.ShowDetail::class,
            AppRoute.ComedianDetail::class,
            AppRoute.ClubDetail::class,
            AppRoute.PodcastDetail::class,
            AppRoute.NotificationCenter::class,
        )

    fun showsTopAppBar(destination: NavDestination?): Boolean =
        destination == null || topAppBarRoutes.any { destination.hasRoute(it) }

    fun showsBottomBar(destination: NavDestination?): Boolean =
        destination == null || bottomBarRoutes.any { destination.hasRoute(it) }
}
