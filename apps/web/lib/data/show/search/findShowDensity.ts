import { formatInTimeZone } from "date-fns-tz";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { Prisma } from "@prisma/client";
import { resolveCanonicalComedianIdentityByName } from "@/lib/data/comedian/detail/resolveCanonicalComedianIdentity";

export type ShowDensity = Record<string, number>;

export async function findShowDensity(
    helper: QueryHelper,
): Promise<ShowDensity> {
    try {
        const zipCodeClause = helper.getZipCodeClause();
        const clubNameClause = helper.getClubNameClause();
        const clubId = helper.params.clubId
            ? Number(helper.params.clubId)
            : undefined;
        const dateClause = helper.getDateClause();
        const comedianIdentity = helper.params.comedian
            ? await resolveCanonicalComedianIdentityByName(
                  helper.params.comedian,
              )
            : null;
        const whereClause: Prisma.ShowWhereInput = {
            ...dateClause,
            club: {
                visible: true,
                ...(clubId !== undefined && { id: clubId }),
                ...(zipCodeClause.zipCode && zipCodeClause),
                ...(clubNameClause.name && clubNameClause),
            },
            ...helper.getLineupItemClause(comedianIdentity?.memberUuids),
        };

        const rows = await db.show.findMany({
            where: whereClause,
            select: { date: true },
        });

        return rows.reduce<ShowDensity>((counts, show) => {
            const key = formatInTimeZone(
                show.date,
                helper.timezone,
                "yyyy-MM-dd",
            );
            counts[key] = (counts[key] ?? 0) + 1;
            return counts;
        }, {});
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findShowDensity:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while fetching show density",
        );
    }
}
