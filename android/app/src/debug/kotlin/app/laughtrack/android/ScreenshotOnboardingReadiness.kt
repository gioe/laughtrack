package app.laughtrack.android

/**
 * Returns whether the onboarding screenshot has reached its canonical populated state.
 *
 * This stays independent of Compose so the instrumentation polling loop and JVM regression
 * tests share the same definition of readiness.
 */
fun isOnboardingScreenshotReady(
    fixtureNamePresent: Boolean,
    fixturePortraitPresent: Boolean,
    passControlPresent: Boolean,
    followControlPresent: Boolean,
    loadingPresent: Boolean,
    emptyStatePresent: Boolean,
): Boolean =
    fixtureNamePresent &&
        fixturePortraitPresent &&
        passControlPresent &&
        followControlPresent &&
        !loadingPresent &&
        !emptyStatePresent
