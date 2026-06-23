package app.laughtrack.android

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * Application entry point. [HiltAndroidApp] generates the Hilt dependency-injection
 * container that backs every Activity, ViewModel, and service in the app — the
 * Android analog of the iOS app's service container / bootstrap.
 */
@HiltAndroidApp
class LaughTrackApplication : Application()
