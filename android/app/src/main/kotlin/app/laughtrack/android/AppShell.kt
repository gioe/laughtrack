package app.laughtrack.android

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.KeyboardArrowDown
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
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.LayoutDirection
import androidx.navigation.NavBackStackEntry
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
import kotlinx.coroutines.flow.first
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
    onNotificationPermissionResult: (Boolean) -> Unit = {},
) {
    val forwardSign = if (LocalLayoutDirection.current == LayoutDirection.Rtl) -1 else 1
    val backStackEntry by navController.currentBackStackEntryAsState()
    // The state flow may not have emitted an already initialized/restored entry yet.
    val currentDestination = backStackEntry?.destination ?: navController.currentDestination
    var pendingExternalClubId by remember { mutableStateOf<Int?>(null) }
    var pendingSearchRequest by remember { mutableStateOf<SearchLaunchRequest?>(null) }

    // Route a deep link / push target once it is delivered, then clear it so a
    // recomposition or config change doesn't re-navigate.
    LaunchedEffect(pendingRoute) {
        pendingRoute?.let {
            // Cold links can arrive before NavHost has installed its graph.
            navController.currentBackStackEntryFlow.first()
            pendingExternalClubId = (it as? AppRoute.ClubDetail)?.id
            navController.openEntity(it)
            onRouteConsumed()
        }
    }

    // NavHost remembers its graph. Keep the destination wrapper current without
    // rebuilding entries, their ViewModels, or saved scroll state on recomposition.
    val latestShellContent =
        rememberUpdatedState<@Composable (NavBackStackEntry, @Composable () -> Unit) -> Unit>(
            { entry, content ->
                AppDestinationSurface(
                    destination = entry.destination,
                    selectedDestination = currentDestination,
                    navController = navController,
                    signedIn = signedIn,
                    playbackController = playbackController,
                    content = content,
                )
            },
        )
    val shellContent: @Composable (NavBackStackEntry, @Composable () -> Unit) -> Unit =
        { entry, content -> latestShellContent.value(entry, content) }

    Box(Modifier.fillMaxSize()) {
        LaughTrackAtmosphereBackground()
        NavHost(
            navController = navController,
            startDestination = appShellStartRoute,
            modifier = Modifier.fillMaxSize(),
            enterTransition = {
                AppShellMotion.enter(initialState.destination, targetState.destination, forwardSign = forwardSign)
            },
            exitTransition = {
                AppShellMotion.exit(
                    initialState.destination,
                    targetState.destination,
                    forwardSign = forwardSign,
                )
            },
            popEnterTransition = {
                AppShellMotion.enter(
                    initialState.destination,
                    targetState.destination,
                    popping = true,
                    forwardSign = forwardSign,
                )
            },
            popExitTransition = {
                AppShellMotion.exit(
                    initialState.destination,
                    targetState.destination,
                    popping = true,
                    forwardSign = forwardSign,
                )
            },
        ) {
            appShellDestination<AppRoute.Discover>(shellContent) {
                HomeScreen(
                    signedIn = signedIn,
                    onOpenEntity = navController::openEntity,
                    onPlay = { item -> playbackController?.play(item) },
                    onOpenSearch = { request ->
                        pendingSearchRequest = request
                        navController.switchTab(AppTab.SEARCH)
                    },
                )
            }
            appShellDestination<AppRoute.Search>(shellContent) {
                SearchScreen(
                    onOpenEntity = navController::openEntity,
                    requestedSearch = pendingSearchRequest,
                    onRequestedSearchConsumed = { pendingSearchRequest = null },
                )
            }
            appShellDestination<AppRoute.Favorites>(shellContent) {
                if (screenshotPersona == null) {
                    LibraryScreen(
                        signedIn = signedIn,
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
            appShellDestination<AppRoute.ComedianOnboarding>(shellContent) {
                ComedianOnboardingScreen(
                    onComplete = {
                        navController.navigate(AppRoute.Discover) {
                            popUpTo(AppRoute.ComedianOnboarding) { inclusive = true }
                            launchSingleTop = true
                        }
                    },
                )
            }

            appShellDestination<AppRoute.ShowDetail>(shellContent) { entry ->
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
            appShellDestination<AppRoute.ComedianDetail>(shellContent) { entry ->
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
                shellContent = shellContent,
                navController = navController,
                pendingExternalClubId = pendingExternalClubId,
                onExternalRouteConsumed = { pendingExternalClubId = null },
            )
            appShellDestination<AppRoute.PodcastDetail>(shellContent) { entry ->
                PodcastDetailScreen(
                    id = entry.toRoute<AppRoute.PodcastDetail>().id,
                    onBack = { navController.popBackStack() },
                    onOpenEntity = navController::openEntity,
                )
            }
            appShellDestination<AppRoute.PodcastEpisodeDetail>(shellContent) { entry ->
                PodcastEpisodeDetailScreen(
                    id = entry.toRoute<AppRoute.PodcastEpisodeDetail>().id,
                    onBack = { navController.popBackStack() },
                    onOpenEntity = navController::openEntity,
                )
            }
            appShellDestination<AppRoute.NowPlaying>(shellContent) {
                Column(Modifier.fillMaxSize().safeDrawingPadding()) {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(
                            Icons.Filled.KeyboardArrowDown,
                            contentDescription = "Collapse player",
                            tint = LaughTrackColors.Foreground,
                        )
                    }
                    Box(Modifier.weight(1f)) {
                        if (playbackController != null) {
                            NowPlayingScreen(playbackController = playbackController)
                        } else {
                            PlaceholderScreen("Now Playing")
                        }
                    }
                }
            }

            appShellDestination<AppRoute.Profile>(shellContent) {
                if (screenshotPersona == null) {
                    ProfileScreen(notificationPermissionControl = {
                        NotificationPermissionControl(onResult = onNotificationPermissionResult)
                    })
                } else {
                    ProfileScreen(stateOverride = screenshotPersona.profileUiState)
                }
            }
            appShellDestination<AppRoute.NotificationCenter>(shellContent) {
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
    }

    // Sign-in prompt for gated actions (a guest tapping favorite). Overlays the
    // whole shell so it appears regardless of the active destination. Mirrors iOS
    // ContentView's login-modal sheet.
    if (showLoginPrompt) {
        LoginPromptSheet(onDismiss = onLoginPromptDismiss)
    }
}

/** Each transitioning entry retains its own chrome and safe areas, including back previews. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppDestinationSurface(
    destination: NavDestination,
    selectedDestination: NavDestination?,
    navController: NavHostController,
    signedIn: Boolean,
    playbackController: PodcastPlaybackController?,
    content: @Composable () -> Unit,
) {
    Box(Modifier.fillMaxSize().background(LaughTrackColors.Canvas)) {
        if (!AppShellBackgrounds.usesOpaqueCanvas(destination)) LaughTrackAtmosphereBackground()
        Scaffold(
            modifier = Modifier.testTag("app-shell-scaffold-${destination.id}"),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0, 0, 0, 0),
            topBar = {
                if (AppShellChrome.showsTopAppBar(destination)) {
                    TopAppBar(
                        title = { Text("LaughTrack") },
                        actions = { ProfileMenu(navController, signedIn) },
                        colors =
                            TopAppBarDefaults.topAppBarColors(
                                containerColor = Color.Transparent,
                                scrolledContainerColor = Color.Transparent,
                            ),
                    )
                }
            },
            bottomBar = {
                if (AppShellChrome.showsBottomBar(destination)) {
                    NavigationBar {
                        AppShellTabs.visibleTabs.forEach { tab ->
                            NavigationBarItem(
                                selected =
                                    AppShellTabs.isSelected(
                                        if (AppShellChrome.showsBottomBar(
                                                selectedDestination,
                                            )
                                        ) {
                                            selectedDestination
                                        } else {
                                            destination
                                        },
                                        tab,
                                    ),
                                onClick = { navController.switchTab(tab) },
                                icon = { Icon(tab.icon, contentDescription = tab.label) },
                                label = { Text(tab.label) },
                            )
                        }
                    }
                }
            },
        ) { padding ->
            Box(Modifier.fillMaxSize().padding(padding).testTag("app-shell-content-${destination.id}")) {
                content()
                if (playbackController != null && AppShellChrome.showsMiniPlayer(destination)) {
                    PodcastMiniPlayer(
                        playbackController = playbackController,
                        onExpand = { navController.openEntity(AppRoute.NowPlaying) },
                        modifier = Modifier.align(Alignment.BottomCenter),
                    )
                }
            }
        }
    }
}

private inline fun <reified T : Any> NavGraphBuilder.appShellDestination(
    noinline shellContent: @Composable (NavBackStackEntry, @Composable () -> Unit) -> Unit,
    noinline content: @Composable (NavBackStackEntry) -> Unit,
) {
    composable<T> { entry -> shellContent(entry) { content(entry) } }
}

private fun NavGraphBuilder.clubDetailDestination(
    shellContent: @Composable (NavBackStackEntry, @Composable () -> Unit) -> Unit,
    navController: NavHostController,
    pendingExternalClubId: Int?,
    onExternalRouteConsumed: () -> Unit,
) {
    appShellDestination<AppRoute.ClubDetail>(shellContent) { entry ->
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
private fun ProfileMenu(
    navController: NavController,
    signedIn: Boolean,
) {
    var expanded by remember { mutableStateOf(false) }
    IconButton(onClick = { expanded = true }) {
        Icon(Icons.Filled.Person, contentDescription = "Profile menu")
    }
    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
        if (signedIn) {
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
        } else {
            DropdownMenuItem(
                text = { Text("Sign up or sign in") },
                onClick = {
                    expanded = false
                    navController.openEntity(AppRoute.Profile)
                },
            )
        }
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

// Keep unresolved chrome aligned with the actual graph start, not a pending
// external route that has not been navigated to yet.
private val appShellStartRoute: AppRoute = AppRoute.Discover

internal object AppShellTabs {
    /** Stable top-level information architecture, independent of auth or library contents. */
    val visibleTabs: List<AppTab> = AppTab.entries

    fun isSelected(
        destination: NavDestination?,
        tab: AppTab,
        initialRoute: AppRoute = appShellStartRoute,
    ): Boolean =
        destination?.hierarchy?.any { it.hasRoute(tab.rootRoute::class) }
            ?: (initialRoute::class == tab.rootRoute::class)
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
            AppRoute.ComedianOnboarding::class,
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

    fun showsTopAppBar(
        destination: NavDestination?,
        initialRoute: AppRoute = appShellStartRoute,
    ): Boolean =
        destination?.let { resolved -> topAppBarRoutes.any { resolved.hasRoute(it) } }
            ?: (initialRoute::class in topAppBarRoutes)

    fun showsBottomBar(
        destination: NavDestination?,
        initialRoute: AppRoute = appShellStartRoute,
    ): Boolean =
        destination?.let { resolved -> bottomBarRoutes.any { resolved.hasRoute(it) } }
            ?: (initialRoute::class in bottomBarRoutes)

    fun showsMiniPlayer(
        destination: NavDestination?,
        initialRoute: AppRoute = appShellStartRoute,
    ): Boolean =
        destination?.let { resolved -> miniPlayerHiddenRoutes.none { resolved.hasRoute(it) } }
            ?: (initialRoute::class !in miniPlayerHiddenRoutes)

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

    fun usesOpaqueCanvas(
        destination: NavDestination?,
        initialRoute: AppRoute = appShellStartRoute,
    ): Boolean =
        destination?.let { resolved -> opaqueRoutes.any { resolved.hasRoute(it) } }
            ?: (initialRoute::class in opaqueRoutes)
}
