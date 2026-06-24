package app.laughtrack.android.core.navigation

/**
 * Specification of the detail back-stack cycle-dedup rule, mirroring the iOS
 * EntityNavigationCoordinator: reopening an entity that is already on the stack
 * pops back to it rather than pushing a duplicate.
 *
 * This is a pure list transform so the rule is unit-tested on the JVM. The
 * Compose binding (`NavController.openEntity` in :app) implements the same
 * contract against the real NavController via pop-back-or-navigate.
 */
object NavStackDedup {
    /**
     * Return the new stack after navigating to [route]. If [route] is already on
     * the stack, truncate to that occurrence (pop-back); otherwise append (push).
     */
    fun navigate(stack: List<AppRoute>, route: AppRoute): List<AppRoute> {
        val existing = stack.indexOf(route)
        return if (existing >= 0) {
            stack.subList(0, existing + 1).toList()
        } else {
            stack + route
        }
    }
}
