import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import {
    COMEDIAN_SELECT,
    buildUpcomingCountSelect,
    mapComedian,
    type ComedianWithUpcomingCount,
} from "../search/findComediansWithCount";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

// Popularity floor for onboarding suggestions. The SQL predicate is strict
// (`> ONBOARDING_POPULARITY_FLOOR`) so onboarding can draw from comedians with
// a popularity score above 0.4 while still filtering out the lowest tail.
export const ONBOARDING_POPULARITY_FLOOR = 0.4;

// Number of suggestions returned per call (matches the onboarding grid).
export const ONBOARDING_SUGGESTION_LIMIT = 12;

/**
 * Popularity-weighted random comedian sample for onboarding.
 *
 * Unlike the shared comedian search (`sort=mostPopular`), which is deterministic
 * popularity-DESC and returns the same top rows every load, this samples a fresh
 * weighted-random set above {@link ONBOARDING_POPULARITY_FLOOR} on each call so
 * favorites aren't funneled into a tiny elite tail.
 *
 * Selection uses the Efraimidis–Spirakis weighted-reservoir key done entirely in
 * SQL: each eligible comedian draws `key = random()^(1/popularity)` and the top-K
 * keys win. Because the key is redrawn per row per call, membership and order vary
 * between calls; because higher popularity shrinks the exponent (popularity ≤ 1),
 * more-popular comedians produce larger keys and are selected more often over many
 * draws. The same eligibility filters as comedian search are applied (deny-list,
 * restrictContent tag, `parent_comedian_id IS NULL`, upcoming-only).
 */
export async function getOnboardingComedianSuggestions(
    profileId?: string,
): Promise<ComedianDTO[]> {
    try {
        const sampledRows = await db.$queryRaw<{ id: number }[]>(
            Prisma.sql`
                SELECT c.id
                FROM "comedians" c
                WHERE c.popularity > ${ONBOARDING_POPULARITY_FLOOR}
                  AND c."has_image" = true
                  AND c.visible = true
                  AND c."parent_comedian_id" IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM "tagged_comedians" tc
                      JOIN "tags" t ON tc."tag_id" = t.id
                      WHERE tc."comedian_id" = c.uuid AND t."restrictContent" = true
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM "comedian_deny_list" dl
                      WHERE dl."name" = c.name
                  )
                  AND EXISTS (
                      SELECT 1 FROM "lineup_items" li
                      JOIN "shows" s ON li."show_id" = s.id
                      WHERE li."comedian_id" = c.uuid AND s.date > NOW()
                  )
                ORDER BY power(random(), 1.0 / c.popularity) DESC
                LIMIT ${ONBOARDING_SUGGESTION_LIMIT}
            `,
        );

        const sampledIds = sampledRows.map((r) => r.id);
        if (sampledIds.length === 0) {
            return [];
        }

        const comedians = await db.comedian.findMany({
            where: { id: { in: sampledIds }, visible: true },
            select: {
                ...COMEDIAN_SELECT,
                ...buildUpcomingCountSelect(),
                ...(profileId
                    ? {
                          favoriteComedians: {
                              where: { profileId },
                              select: { id: true },
                          },
                      }
                    : {}),
            },
        });

        // findMany ignores the `id IN (...)` order, so re-apply the weighted-random
        // ordering produced by the sampling query before mapping.
        const idOrder = new Map(sampledIds.map((id, i) => [id, i]));
        return (comedians as ComedianWithUpcomingCount[])
            .sort((a, b) => (idOrder.get(a.id) ?? 0) - (idOrder.get(b.id) ?? 0))
            .map(mapComedian);
    } catch (error) {
        console.error("Error in getOnboardingComedianSuggestions:", error);
        throw new Error("Failed to fetch onboarding comedian suggestions");
    }
}
