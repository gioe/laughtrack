package app.laughtrack.android

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavController
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
import app.laughtrack.android.feature.home.HomeScreen

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
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination

    // Route a deep link / push target once it is delivered, then clear it so a
    // recomposition or config change doesn't re-navigate.
    LaunchedEffect(pendingRoute) {
        pendingRoute?.let {
            navController.openEntity(it)
            onRouteConsumed()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("LaughTrack") },
                actions = { ProfileMenu(navController) },
            )
        },
        bottomBar = {
            NavigationBar {
                AppTab.entries.forEach { tab ->
                    val selected = currentDestination?.hierarchy?.any {
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
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = AppRoute.Discover,
            modifier = Modifier.fillMaxSize().padding(padding),
        ) {
            composable<AppRoute.Discover> { HomeScreen() }
            // The real Search/Favorites screens land in TASK-3260 / TASK-3261. The
            // sample affordance exercises the detail stack (push + cycle-dedup) in
            // the shell until those screens provide real cards.
            composable<AppRoute.Search> {
                PlaceholderScreen("Search", onOpenSample = { navController.openEntity(AppRoute.ShowDetail(1)) })
            }
            composable<AppRoute.Favorites> { PlaceholderScreen("Favorites") }

            composable<AppRoute.ShowDetail> { entry ->
                EntityDetailPlaceholder("Show", entry.toRoute<AppRoute.ShowDetail>().id) { navController.popBackStack() }
            }
            composable<AppRoute.ComedianDetail> { entry ->
                EntityDetailPlaceholder("Comedian", entry.toRoute<AppRoute.ComedianDetail>().id) { navController.popBackStack() }
            }
            composable<AppRoute.ClubDetail> { entry ->
                EntityDetailPlaceholder("Club", entry.toRoute<AppRoute.ClubDetail>().id) { navController.popBackStack() }
            }
            composable<AppRoute.PodcastDetail> { entry ->
                EntityDetailPlaceholder("Podcast", entry.toRoute<AppRoute.PodcastDetail>().id) { navController.popBackStack() }
            }

            composable<AppRoute.Profile> { PlaceholderScreen("Profile") }
            composable<AppRoute.NotificationCenter> { PlaceholderScreen("Notifications") }
        }
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
    get() = when (this) {
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
 */
fun NavController.openEntity(route: AppRoute) {
    if (!popBackStack(route, inclusive = false)) {
        navigate(route)
    }
}
