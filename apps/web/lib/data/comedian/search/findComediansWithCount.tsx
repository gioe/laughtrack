import { db } from "@/lib/db";
import {
    QueryHelper,
    COMEDIAN_SORT_MAP,
    COMEDIAN_SORT_MAP_ADMIN,
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
    hasImage: true,
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
        imageUrl: buildComedianImageUrl(
            effectiveComedian.name,
            effectiveComedian.hasImage,
        ),
        hasImage: Boolean(effectiveComedian.hasImage),
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

async function fetchDeniedComedianNames(): Promise<string[]> {
    // Errors propagate so a missing / broken deny_list surfaces loudly rather
    // than silently re-exposing the event-title rows this filter is meant to hide.
    const rows = await db.$queryRaw<{ name: string }[]>(
        Prisma.sql`SELECT name FROM "comedian_deny_list"`,
    );
    return rows.map((r) => r.name);
}

export async function findComediansWithCount(
    helper: QueryHelper,
): Promise<ComediansResponse> {
    const sortMap = helper.isAdmin
        ? COMEDIAN_SORT_MAP_ADMIN
        : COMEDIAN_SORT_MAP;
    try {
        const includeEmpty = helper.params.includeEmpty === "true";
        const deniedNames = await fetchDeniedComedianNames();
        // Compose with AND: name-contains search and name-notIn deny list both target
        // the `name` column, so spreading them as sibling keys would clobber one.
        const nameFilters: Prisma.ComedianWhereInput[] = [
            helper.getComedianNameClause(),
            ...(deniedNames.length > 0
                ? [{ name: { notIn: deniedNames } }]
                : []),
        ];

        const hasZipFilter = Boolean(helper.params.zip);
        const hasDateFilter = Boolean(
            helper.params.fromDate || helper.params.toDate,
        );
        const needsLineupItemsFilter =
            !includeEmpty || hasZipFilter || hasDateFilter;

        // Filter shows by date range (explicit) or restrict to upcoming when
        // !includeEmpty (default comedian-search path, where we don't want to
        // surface comedians whose only shows are in the past). Optionally also
        // restrict to clubs in the zip-code radius.
        const showFilter: Prisma.ShowWhereInput = {};
        if (hasDateFilter) {
            Object.assign(showFilter, helper.getDateClause());
        }
        // Apply upcoming-only default when no effective date filter landed —
        // covers both no-params and set-but-invalid-params cases, since
        // getDateClause returns {} in both.
        if (!showFilter.date && !includeEmpty) {
            showFilter.date = { gte: new Date() };
        }
        if (hasZipFilter) {
            showFilter.club = helper.getZipCodeClause();
        }

        const lineupItemsClause: Prisma.ComedianWhereInput =
            needsLineupItemsFilter
                ? { lineupItems: { some: { show: showFilter } } }
                : {};

        // Build the scope predicates that constrain the "upcoming shows" count —
        // the same zip + date bounds the user applied in the modal — so the
        // minUpcomingShows threshold, the ShowCount ORDER BY, and the raw-SQL
        // WHERE all count the same set of shows. Hoisted above both branches so
        // the Prisma path's pre-fetch can share it.
        const showWhereParts: Prisma.Sql[] = [];
        if (hasDateFilter || !includeEmpty) {
            const dateBounds = (showFilter as { date?: Prisma.DateTimeFilter })
                .date;
            const gte = dateBounds?.gte;
            const lte = dateBounds?.lte;
            if (gte !== undefined) {
                showWhereParts.push(
                    Prisma.sql`s.date >= ${new Date(gte as string | Date)}`,
                );
            }
            if (lte !== undefined) {
                showWhereParts.push(
                    Prisma.sql`s.date <= ${new Date(lte as string | Date)}`,
                );
            }
        }
        const zipFilter = (
            showFilter.club as {
                zipCode?: { in?: string[]; equals?: string };
            }
        )?.zipCode;
        const zipList: string[] | null = zipFilter
            ? Array.isArray(zipFilter.in)
                ? zipFilter.in
                : typeof zipFilter.equals === "string"
                  ? [zipFilter.equals]
                  : null
            : null;
        if (zipList && zipList.length > 0) {
            showWhereParts.push(
                Prisma.sql`cl."zip_code" IN (${Prisma.join(zipList)})`,
            );
        } else if (zipList && zipList.length === 0) {
            // Resolved to no zips (city not found) — match nothing.
            showWhereParts.push(Prisma.sql`FALSE`);
        }

        // Returns the parenthesized COUNT subquery for comedian c.uuid's shows
        // matching the active scope. Used 3x (pre-fetch WHERE, show_count WHERE
        // threshold, show_count ORDER BY) — a single source of truth so a fix
        // to the scoping semantics only has to be made in one place.
        const buildScopedUpcomingCountSql = (): Prisma.Sql => {
            const joinClause = zipList
                ? Prisma.sql`JOIN "clubs" cl ON s."club_id" = cl.id`
                : Prisma.sql``;
            const whereClause =
                showWhereParts.length > 0
                    ? Prisma.sql`AND ${Prisma.join(showWhereParts, " AND ")}`
                    : Prisma.sql`AND s.date > NOW()`;
            return Prisma.sql`(
                SELECT COUNT(*) FROM "lineup_items" li
                JOIN "shows" s ON li."show_id" = s.id
                ${joinClause}
                WHERE li."comedian_id" = c.uuid ${whereClause}
            )`;
        };

        const isShowCountSort =
            helper.params.sort === SortParamValue.ShowCountDesc ||
            helper.params.sort === SortParamValue.ShowCountAsc;

        // Prisma can't express "COUNT(relation WHERE ...) >= N" in a where clause,
        // so resolve matching comedian uuids via a raw SQL pre-fetch and pass
        // them to the main findMany/count via `uuid IN (...)`. Skipped on the
        // show_count sort path — that branch's own whereConditions apply the
        // same threshold directly, so the pre-fetch would just be duplicate
        // work with a discarded result.
        const minUpcomingShowsValue =
            Number(helper.params.minUpcomingShows) || 0;
        let minUpcomingShowsClause: Prisma.ComedianWhereInput = {};
        if (minUpcomingShowsValue > 0 && !isShowCountSort) {
            const matchingRows = await db.$queryRaw<{ uuid: string }[]>(
                Prisma.sql`
                    SELECT c.uuid FROM "comedians" c
                    WHERE ${buildScopedUpcomingCountSql()} >= ${minUpcomingShowsValue}
                `,
            );
            if (matchingRows.length === 0) {
                return { comedians: [], totalCount: 0 };
            }
            minUpcomingShowsClause = {
                uuid: { in: matchingRows.map((r) => r.uuid) },
            };
        }

        const whereClause: Prisma.ComedianWhereInput = {
            ...helper.getComedianFiltersClause(),
            parentComedian: {
                is: null,
            },
            AND: nameFilters,
            ...lineupItemsClause,
            ...minUpcomingShowsClause,
        };

        const upcomingCountSelect = buildUpcomingCountSelect();

        // Get total count first
        const totalCount = await db.comedian.count({ where: whereClause });

        // For show_count_desc / show_count_asc: use raw SQL to ORDER BY upcoming show count
        // with DB-level LIMIT/OFFSET, then fetch full comedian data for only that page's IDs.
        if (isShowCountSort) {
            const { take, skip } = helper.getGenericClauses(
                totalCount,
                sortMap,
            );

            // Build parameterized WHERE conditions mirroring the Prisma whereClause
            const whereConditions: Prisma.Sql[] = [
                Prisma.sql`c."parent_comedian_id" IS NULL`,
                Prisma.sql`NOT EXISTS (
                    SELECT 1 FROM "tagged_comedians" tc
                    JOIN "tags" t ON tc."tag_id" = t.id
                    WHERE tc."comedian_id" = c.uuid AND t."restrictContent" = true
                )`,
                Prisma.sql`NOT EXISTS (
                    SELECT 1 FROM "comedian_deny_list" dl
                    WHERE dl."name" = c.name
                )`,
            ];

            const comedianName = helper.params.comedian;
            if (comedianName) {
                whereConditions.push(
                    Prisma.sql`c.name ILIKE ${"%" + comedianName + "%"}`,
                );
            }

            const lineupExistsClause =
                showWhereParts.length > 0
                    ? Prisma.sql`EXISTS (
                        SELECT 1 FROM "lineup_items" li
                        JOIN "shows" s ON li."show_id" = s.id
                        ${zipList ? Prisma.sql`JOIN "clubs" cl ON s."club_id" = cl.id` : Prisma.sql``}
                        WHERE li."comedian_id" = c.uuid AND ${Prisma.join(showWhereParts, " AND ")}
                    )`
                    : null;
            if (lineupExistsClause) {
                whereConditions.push(lineupExistsClause);
            }

            if (minUpcomingShowsValue > 0) {
                whereConditions.push(
                    Prisma.sql`${buildScopedUpcomingCountSql()} >= ${minUpcomingShowsValue}`,
                );
            }

            const filtersParam = helper.params.filters;
            if (filtersParam) {
                whereConditions.push(
                    Prisma.sql`EXISTS (
                        SELECT 1 FROM "tagged_comedians" tc2
                        JOIN "tags" t2 ON tc2."tag_id" = t2.id
                        WHERE tc2."comedian_id" = c.uuid
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
                    FROM "comedians" c
                    WHERE ${Prisma.join(whereConditions, " AND ")}
                    ORDER BY ${buildScopedUpcomingCountSql()} ${sortDir}, c.name ASC
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
            sortMap,
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
