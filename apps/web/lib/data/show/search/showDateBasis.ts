import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { isValidTimezone } from "@/util/timezone";

/** Missing or invalid venue zones follow the caller, matching native tickets. */
export function showDateTimezone(
    venueTimezone: string | null | undefined,
    fallback: string,
): string {
    return venueTimezone && isValidTimezone(venueTimezone)
        ? venueTimezone
        : fallback;
}

/** Apply venue civil dates before counting/pagination; legacy callers keep request dates. */
export async function buildShowDateClause(
    helper: QueryHelper,
    clubWhere: Prisma.ClubWhereInput,
): Promise<Prisma.ShowWhereInput> {
    const requestClause = helper.getDateClause();
    if (
        helper.params.dateBasis !== "venue" ||
        Object.keys(requestClause).length === 0
    ) {
        return requestClause;
    }
    const venues = await db.club.groupBy({
        where: clubWhere,
        by: ["timezone"],
    });
    // Distinct metadata is bounded by the number of timezone identifiers, not shows.
    // Keep each stored value in its branch so null/invalid values use the fallback
    // without accidentally matching another venue's date interval.
    return {
        OR: venues.map(({ timezone }) => ({
            club: { timezone },
            ...helper.getDateClause(
                showDateTimezone(timezone, helper.timezone),
                true,
            ),
        })),
    };
}
