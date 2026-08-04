package app.laughtrack.android

import androidx.compose.foundation.background
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
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavController
import androidx.navigation.NavDestination
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.AppTab
import app.laughtrack.android.core.navigation.SearchDestination
import app.laughtrack.android.core.navigation.SearchLaunchRequest
import app.laughtrack.android.core.playback.NowPlayingScreen
import app.laughtrack.android.core.playback.PodcastMiniPlayer
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.ui.components.LaughTrackAtmosphereBackground
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.ui.ClubDetailScreen
import app.laughtrack.android.feature.detail.ui.ComedianDetailScreen
import app.laughtrack.android.feature.detail.ui.PodcastDetailScreen
import app.laughtrack.android.feature.detail.ui.PodcastEpisodeDetailScreen
import app.laughtrack.android.feature.detail.ui.ShowDetailScreen
import app.laughtrack.android.feature.home.HomeScreen
import app.laughtrack.android.feature.library.LibrarySavedDestination
import app.laughtrack.android.feature.library.LibraryScreen
import app.laughtrack.android.feature.library.LibrarySearchSeed
import app.laughtrack.android.feature.notifications.NotificationCenterScreen
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingScreen
import app.laughtrack.android.feature.profile.LoginPromptSheet
import app.laughtrack.android.feature.profile.ProfileScreen
import app.laughtrack.android.feature.search.ui.SearchScreen
import app.laughtrack.android.screenshots.AuthenticatedScreenshotPersona
import kotlin.reflect.KClass

/**
 * Root app shell: a permanent three-tab bottom bar (Discover/Search/Library) over a typed
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
    playbackController: PodcastPlaybackController? = null,
    showLoginPrompt: Boolean = false,
    onLoginPromptDismiss: () -> Unit = {},
    screenshotPersona: AuthenticatedScreenshotPersona? = null,
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination
    var pendingExternalClubId by remember { mutableStateOf<Int?>(null) }
    var pendingSearchRequest by remember { mutableStateOf<SearchLaunchRequest?>(null) }
    val usesOpaqueCanvas = AppShellBackgrounds.usesOpaqueCanvas(currentDestination)
    val topAppBarContainerColor = if (usesOpaqueCanvas) LaughTrackColors.Canvas else Color.Transparent

    // Route a deep link / push target once it is delivered, then clear it so a
    // recomposition or config change doesn't re-navigate.
    LaunchedEffect(pendingRoute) {
        pendingRoute?.let {
            pendingExternalClubId = (it as? AppRoute.ClubDetail)?.id
            navController.openEntity(it)
            onRouteConsumed()
        }
    }

    Box(Modifier.fillMaxSize()) {
        LaughTrackAtmosphereBackground()

        Scaffold(
            containerColor = Color.Transparent,
            // TopAppBar/NavigationBar and detail heroes own their respective safe-area
            // padding. Reserving safeDrawing here as well leaves an opaque status-bar
            // strip above detail artwork instead of allowing true edge-to-edge chrome.
            contentWindowInsets = WindowInsets(0, 0, 0, 0),
            topBar = {
                if (AppShellChrome.showsTopAppBar(currentDestination)) {
                    TopAppBar(
                        title = { Text("LaughTrack") },
                        actions = { ProfileMenu(navController) },
                        colors =
                            TopAppBarDefaults.topAppBarColors(
                                containerColor = topAppBarContainerColor,
                                scrolledContainerColor = topAppBarContainerColor,
                            ),
                    )
                }
            },
            bottomBar = {
                if (AppShellChrome.showsBottomBar(currentDestination)) {
                    NavigationBar {
                        AppShellTabs.visibleTabs.forEach { tab ->
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
                        HomeScreen(
                            signedIn = signedIn,
                            onOpenEntity = navController::openEntity,
                            onOpenSearch = { request ->
                                pendingSearchRequest = request
                                navController.switchTab(AppTab.SEARCH)
                            },
                        )
                    }
                    composable<AppRoute.Search> {
                        SearchScreen(
                            onOpenEntity = navController::openEntity,
                            requestedSearch = pendingSearchRequest,
                            onRequestedSearchConsumed = { pendingSearchRequest = null },
                        )
                    }
                    composable<AppRoute.Favorites> { entry ->
                        val scopedShowIds = entry.toRoute<AppRoute.Favorites>().showIds
                        if (screenshotPersona == null) {
                            LibraryScreen(
                                signedIn = signedIn,
                                scopedShowIds = scopedShowIds,
                                onOpenProfile = { navController.openEntity(AppRoute.Profile) },
                                onOpenShow = { showId ->
                                    navController.openEntity(AppRoute.ShowDetail(showId))
                                },
                                onOpenSaved = { destination ->
                                    navController.openEntity(destination.toAppRoute())
                                },
                                onOpenSearch = { seed ->
                                    pendingSearchRequest = seed.toSearchRequest()
                                    navController.switchTab(AppTab.SEARCH)
                                },
                            )
                        } else {
                            LibraryScreen(
                                signedIn = true,
                                scopedShowIds = scopedShowIds,
                                onOpenProfile = { navController.openEntity(AppRoute.Profile) },
                                snapshotOverride = screenshotPersona.favoritesSnapshot,
                                savedShowsSnapshotOverride = screenshotPersona.savedShowsSnapshot,
                                onOpenShow = { showId ->
                                    navController.openEntity(AppRoute.ShowDetail(showId))
                                },
                                onOpenSaved = { destination ->
                                    navController.openEntity(destination.toAppRoute())
                                },
                                onOpenSearch = { seed ->
                                    pendingSearchRequest = seed.toSearchRequest()
                                    navController.switchTab(AppTab.SEARCH)
                                },
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
                        val route = entry.toRoute<AppRoute.ComedianDetail>()
                        ComedianDetailScreen(
                            id = route.id,
                            scopedShowIds = route.showIds,
                            onBack = { navController.popBackStack() },
                            onOpenEntity = navController::openEntity,
                            onPlay = { item -> playbackController?.play(item) },
                        )
                    }
                    clubDetailDestination(
                        navController = navController,
                        pendingExternalClubId = pendingExternalClubId,
                        onExternalRouteConsumed = { pendingExternalClubId = null },
                    )
                    composable<AppRoute.PodcastDetail> { entry ->
                        PodcastDetailScreen(
                            id = entry.toRoute<AppRoute.PodcastDetail>().id,
                            onBack = { navController.popBackStack() },
                            onOpenEntity = navController::openEntity,
                        )
                    }
                    composable<AppRoute.PodcastEpisodeDetail> { entry ->
                        PodcastEpisodeDetailScreen(
                            id = entry.toRoute<AppRoute.PodcastEpisodeDetail>().id,
                            onBack = { navController.popBackStack() },
                            onOpenEntity = navController::openEntity,
                        )
                    }
                    composable<AppRoute.NowPlaying> {
                        Box(
                            Modifier
                                .fillMaxSize()
                                .background(LaughTrackColors.Canvas),
                        ) {
                            if (playbackController != null) {
                                NowPlayingScreen(playbackController = playbackController)
                            } else {
                                PlaceholderScreen("Now Playing")
                            }
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

                if (playbackController != null && AppShellChrome.showsMiniPlayer(currentDestination)) {
                    PodcastMiniPlayer(
                        playbackController = playbackController,
                        onExpand = { navController.openEntity(AppRoute.NowPlaying) },
                        modifier = Modifier.align(Alignment.BottomCenter),
                    )
                }
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

private fun NavGraphBuilder.clubDetailDestination(
    navController: NavHostController,
    pendingExternalClubId: Int?,
    onExternalRouteConsumed: () -> Unit,
) {
    composable<AppRoute.ClubDetail> { entry ->
        val route = entry.toRoute<AppRoute.ClubDetail>()
        val enteredExternally =
            entry.savedStateHandle.get<Boolean>(EXTERNAL_CLUB_ENTRY_KEY)
                ?: (pendingExternalClubId == route.id)
        val previousIsDiscover =
            navController.previousBackStackEntry
                ?.destination
                ?.hasRoute(AppRoute.Discover::class) == true

        LaunchedEffect(entry.id, enteredExternally) {
            entry.savedStateHandle[EXTERNAL_CLUB_ENTRY_KEY] = enteredExternally
            if (enteredExternally && pendingExternalClubId == route.id) {
                onExternalRouteConsumed()
            }
        }

        ClubDetailScreen(
            id = route.id,
            onBack = { navController.popBackStack() },
            onHome =
                if (
                    AppShellChrome.showsClubDetailHome(
                        previousIsDiscover = previousIsDiscover,
                        enteredExternally = enteredExternally,
                    )
                ) {
                    {
                        navController.navigate(AppRoute.Discover) {
                            popUpTo(AppRoute.Discover) { inclusive = false }
                            launchSingleTop = true
                        }
                    }
                } else {
                    null
                },
            onOpenEntity = navController::openEntity,
        )
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

private fun LibrarySavedDestination.toAppRoute(): AppRoute =
    when (this) {
        is LibrarySavedDestination.Comedian -> AppRoute.ComedianDetail(id)
        is LibrarySavedDestination.Club -> AppRoute.ClubDetail(id)
        is LibrarySavedDestination.Podcast -> AppRoute.PodcastDetail(id)
    }

private fun LibrarySearchSeed.toSearchRequest(): SearchLaunchRequest =
    SearchLaunchRequest(
        destination =
            when (this) {
                LibrarySearchSeed.SHOWS -> SearchDestination.SHOWS
                LibrarySearchSeed.COMEDIANS -> SearchDestination.COMEDIANS
                LibrarySearchSeed.CLUBS -> SearchDestination.CLUBS
                LibrarySearchSeed.PODCASTS -> SearchDestination.PODCASTS
            },
        inheritCurrentLocation = nearMe,
    )

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
    /** Stable top-level information architecture, independent of auth or library contents. */
    val visibleTabs: List<AppTab> = AppTab.entries
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
            AppRoute.PodcastEpisodeDetail::class,
            AppRoute.NowPlaying::class,
            AppRoute.NotificationCenter::class,
        )

    /** Expanded playback owns the whole surface; every other destination keeps the mini-player. */
    val miniPlayerHiddenRoutes: Set<KClass<out AppRoute>> = setOf(AppRoute.NowPlaying::class)

    fun showsTopAppBar(destination: NavDestination?): Boolean =
        destination == null || topAppBarRoutes.any { destination.hasRoute(it) }

    fun showsBottomBar(destination: NavDestination?): Boolean =
        destination == null || bottomBarRoutes.any { destination.hasRoute(it) }

    fun showsMiniPlayer(destination: NavDestination?): Boolean =
        destination == null || miniPlayerHiddenRoutes.none { destination.hasRoute(it) }

    /** Home is redundant only for an in-app Discover -> ClubDetail push. */
    fun showsClubDetailHome(
        previousIsDiscover: Boolean,
        enteredExternally: Boolean,
    ): Boolean = enteredExternally || !previousIsDiscover
}

private const val EXTERNAL_CLUB_ENTRY_KEY = "club-detail-entered-externally"

internal object AppShellBackgrounds {
    /** Specialized immersive routes that intentionally replace the inherited app atmosphere. */
    val opaqueRoutes: Set<KClass<out AppRoute>> = setOf(AppRoute.NowPlaying::class)

    fun usesOpaqueCanvas(destination: NavDestination?): Boolean =
        destination != null && opaqueRoutes.any { destination.hasRoute(it) }
}
