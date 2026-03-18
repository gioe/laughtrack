import { db } from "@/lib/db";
import {
    QueryHelper,
    COMEDIAN_SORT_MAP,
} from "@/objects/class/query/QueryHelper";
import {
    containsAliasTag,
    getEffectiveComedian,
} from "@/util/comedian/comedianUtil";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { SortParamValue } from "@/objects/enum/sortParamValue";
import { Prisma } from "@prisma/client";
import { ComediansResponse } from "./interface";

const COMEDIAN_SELECT = {
    id: true,
    uuid: true,
    name: true,
    linktree: true,
    instagramAccount: true,
    instagramFollowers: true,
    tiktokAccount: true,
    tiktokFollowers: true,
    youtubeAccount: true,
    youtubeFollowers: true,
    website: true,
    popularity: true,
    alternativeNames: {
        select: {
            id: true,
            name: true,
            uuid: true,
            linktree: true,
            instagramAccount: true,
            instagramFollowers: true,
            tiktokAccount: true,
            tiktokFollowers: true,
            youtubeAccount: true,
            youtubeFollowers: true,
            website: true,
            popularity: true,
        },
    },
    taggedComedians: {
        select: {
            tag: true,
        },
    },
} as const;

// _count select is built fresh per request to avoid capturing a stale module-load Date
function buildUpcomingCountSelect() {
    return {
        _count: {
            select: {
                lineupItems: {
                    where: {
                        show: { date: { gt: new Date() } },
                    },
                },
            },
        },
    } as const;
}

type ComedianWithUpcomingCount = Prisma.ComedianGetPayload<{
    select: typeof COMEDIAN_SELECT &
        ReturnType<typeof buildUpcomingCountSelect>;
}> & { favoriteComedians?: { id: number }[] };

function mapComedian(comedian: ComedianWithUpcomingCount) {
    const effectiveComedian = getEffectiveComedian(comedian);
    const isAlias = containsAliasTag(effectiveComedian.taggedComedians ?? []);

    return {
        id: effectiveComedian.id,
        name: effectiveComedian.name,
        imageUrl: buildComedianImageUrl(effectiveComedian.name),
        isAlias,
        uuid: effectiveComedian.uuid,
        isFavorite: Boolean(comedian.favoriteComedians?.length),
        social_data: {
            id: effectiveComedian.id,
            linktree: effectiveComedian.linktree,
            instagram_account: effectiveComedian.instagramAccount,
            instagram_followers: effectiveComedian.instagramFollowers,
            tiktok_account: effectiveComedian.tiktokAccount,
            tiktok_followers: effectiveComedian.tiktokFollowers,
            youtube_account: effectiveComedian.youtubeAccount,
            youtube_followers: effectiveComedian.youtubeFollowers,
            website: effectiveComedian.website,
            popularity: effectiveComedian.popularity,
        },
        show_count: comedian._count.lineupItems,
    };
}

export async function findComediansWithCount(
    helper: QueryHelper,
): Promise<ComediansResponse> {
    try {
        const whereClause: Prisma.ComedianWhereInput = {
            ...helper.getComedianNameClause(),
            ...helper.getComedianFiltersClause(),
            parentComedian: {
                is: null,
            },
        };

        const upcomingCountSelect = buildUpcomingCountSelect();

        // Get total count first
        const totalCount = await db.comedian.count({ where: whereClause });

        // For show_count_desc / show_count_asc: use raw SQL to ORDER BY upcoming show count
        // with DB-level LIMIT/OFFSET, then fetch full comedian data for only that page's IDs.
        if (
            helper.params.sort === SortParamValue.ShowCountDesc ||
            helper.params.sort === SortParamValue.ShowCountAsc
        ) {
            const { take, skip } = helper.getGenericClauses(
                totalCount,
                COMEDIAN_SORT_MAP,
            );

            // Build parameterized WHERE conditions mirroring the Prisma whereClause
            const whereConditions: Prisma.Sql[] = [
                Prisma.sql`c."parentComedianId" IS NULL`,
                Prisma.sql`NOT EXISTS (
                    SELECT 1 FROM "TaggedComedian" tc
                    JOIN "Tag" t ON tc."tagId" = t.id
                    WHERE tc."comedianId" = c.id AND t."restrictContent" = true
                )`,
            ];

            const comedianName = helper.params.comedian;
            if (comedianName) {
                whereConditions.push(
                    Prisma.sql`c.name ILIKE ${"%" + comedianName + "%"}`,
                );
            }

            const filtersParam = helper.params.filters;
            if (filtersParam) {
                whereConditions.push(
                    Prisma.sql`EXISTS (
                        SELECT 1 FROM "TaggedComedian" tc2
                        JOIN "Tag" t2 ON tc2."tagId" = t2.id
                        WHERE tc2."comedianId" = c.id
                          AND t2.slug IN (${Prisma.join(filtersParam.split(","))})
                          AND t2.type = 'comedian'
                    )`,
                );
            }

            const sortDir =
                helper.params.sort === SortParamValue.ShowCountAsc
                    ? Prisma.sql`ASC`
                    : Prisma.sql`DESC`;

            const sortedRows = await db.$queryRaw<{ id: number }[]>(
                Prisma.sql`
                    SELECT c.id
                    FROM "Comedian" c
                    WHERE ${Prisma.join(whereConditions, " AND ")}
                    ORDER BY (
                        SELECT COUNT(*) FROM "LineupItem" li
                        JOIN "Show" s ON li."showId" = s.id
                        WHERE li."comedianId" = c.id AND s.date > NOW()
                    ) ${sortDir}, c.name ASC
                    LIMIT ${take} OFFSET ${skip}
                `,
            );

            const comedianIds = sortedRows.map((r) => r.id);

            if (comedianIds.length === 0) {
                return { comedians: [], totalCount };
            }

            const comediansById = await db.comedian.findMany({
                where: { id: { in: comedianIds } },
                select: {
                    ...COMEDIAN_SELECT,
                    ...upcomingCountSelect,
                    ...(helper.getProfileId()
                        ? {
                              favoriteComedians: {
                                  where: {
                                      profileId: helper.getProfileId(),
                                  },
                                  select: { id: true },
                              },
                          }
                        : {}),
                },
            });

            // Re-sort to match the SQL ordering
            const idOrder = new Map(comedianIds.map((id, i) => [id, i]));
            const sorted = (comediansById as ComedianWithUpcomingCount[]).sort(
                (a, b) => (idOrder.get(a.id) ?? 0) - (idOrder.get(b.id) ?? 0),
            );

            return {
                comedians: sorted.map(mapComedian),
                totalCount,
            };
        }

        const { orderBy, take, skip } = helper.getGenericClauses(
            totalCount,
            COMEDIAN_SORT_MAP,
        );
        // Inject totalShows tiebreaker after the primary sort so more-active comedians
        // surface first among ties — skip when already sorting by totalShows to
        // avoid a duplicate orderBy entry.
        const primaryField = Object.keys(orderBy[0])[0];
        const comedianOrderBy =
            primaryField === "totalShows"
                ? orderBy
                : [
                      orderBy[0],
                      { totalShows: "desc" as const },
                      ...orderBy.slice(1),
                  ];

        const filteredComedians = await db.comedian.findMany({
            where: whereClause,
            select: {
                ...COMEDIAN_SELECT,
                ...upcomingCountSelect,
                ...(helper.getProfileId()
                    ? {
                          favoriteComedians: {
                              where: {
                                  profileId: helper.getProfileId(),
                              },
                              select: {
                                  id: true,
                              },
                          },
                      }
                    : {}),
            },
            orderBy: comedianOrderBy,
            take,
            skip,
        });

        return {
            comedians: (filteredComedians as ComedianWithUpcomingCount[]).map(
                mapComedian,
            ),
            totalCount,
        };
    } catch (error) {
        console.error("Error in findComediansWithCount:", error);
        throw new Error("Failed to fetch comedians");
    }
}
