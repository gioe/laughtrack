package app.laughtrack.android.screenshots

import app.laughtrack.android.feature.home.location.HomeLocationModule
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import dagger.Binds
import dagger.Module
import dagger.hilt.components.SingletonComponent
import dagger.hilt.testing.TestInstallIn
import javax.inject.Inject

/**
 * Deterministic [HomeLocationResolver] for App Store / Play screenshot runs: always
 * resolves to Hollywood (90028), so the Near Me rail renders LA shows instead of leaking
 * the emulator/CI runner's IP-based geolocation. Android counterpart to the iOS
 * `-UITestMockMode` 90028 seed — but purely test-side, with no production logic branch.
 *
 * The fake short-circuits FusedLocationProvider + Geocoder entirely, so it returns 90028
 * even on a headless emulator with no GPS fix and no location permission granted.
 *
 * NOTE for the screenshot test (TASK-3616): `HomeViewModel` only consults the resolver
 * from `useDeviceLocation()` (a user action) — NOT on initial load, which requests
 * `zip = null` (server geo-IP inference). The screenshot flow must therefore trigger
 * use-device-location to pin the Near Me rail to 90028; simply installing this fake does
 * not change the first, untriggered feed load.
 */
class FakeHomeLocationResolver
    @Inject
    constructor() : HomeLocationResolver {
        override suspend fun resolveZip(): String = SCREENSHOT_ZIP

        companion object {
            /** Hollywood, CA — dense LA comedy scene for a lively screenshot feed. */
            const val SCREENSHOT_ZIP = "90028"
        }
    }

/**
 * Replaces [HomeLocationModule] across every instrumented test (installed into the real
 * app graph via the Hilt test runner). Only the resolver binding is swapped; the
 * HomeFeed repository/cache bindings live in a separate module and are untouched.
 */
@Module
@TestInstallIn(components = [SingletonComponent::class], replaces = [HomeLocationModule::class])
abstract class FakeHomeLocationModule {
    @Binds
    abstract fun bindFakeHomeLocationResolver(resolver: FakeHomeLocationResolver): HomeLocationResolver
}
