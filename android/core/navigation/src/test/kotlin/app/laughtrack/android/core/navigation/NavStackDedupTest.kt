package app.laughtrack.android.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Test

class NavStackDedupTest {
    @Test
    fun pushes_a_new_route_onto_the_stack() {
        val stack = listOf<AppRoute>(AppRoute.ShowDetail(1))
        assertEquals(
            listOf(AppRoute.ShowDetail(1), AppRoute.ComedianDetail(2)),
            NavStackDedup.navigate(stack, AppRoute.ComedianDetail(2)),
        )
    }

    @Test
    fun reopening_an_on_stack_entity_pops_back_to_it() {
        val stack = listOf<AppRoute>(
            AppRoute.ShowDetail(1),
            AppRoute.ComedianDetail(2),
            AppRoute.ClubDetail(3),
        )
        // Reopening ShowDetail(1) truncates back to it rather than re-pushing.
        assertEquals(
            listOf(AppRoute.ShowDetail(1)),
            NavStackDedup.navigate(stack, AppRoute.ShowDetail(1)),
        )
    }

    @Test
    fun reopening_a_middle_entry_drops_everything_above_it() {
        val stack = listOf<AppRoute>(
            AppRoute.ShowDetail(1),
            AppRoute.ComedianDetail(2),
            AppRoute.ClubDetail(3),
        )
        assertEquals(
            listOf(AppRoute.ShowDetail(1), AppRoute.ComedianDetail(2)),
            NavStackDedup.navigate(stack, AppRoute.ComedianDetail(2)),
        )
    }

    @Test
    fun distinct_ids_of_the_same_entity_type_are_not_deduped() {
        val stack = listOf<AppRoute>(AppRoute.ShowDetail(1))
        assertEquals(
            listOf(AppRoute.ShowDetail(1), AppRoute.ShowDetail(2)),
            NavStackDedup.navigate(stack, AppRoute.ShowDetail(2)),
        )
    }
}
