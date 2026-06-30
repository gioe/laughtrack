import { db } from "@/lib/db";
import { LINEUP_COMEDIAN_SELECT } from "@/lib/data/comedian/lineupComedianSelect";
import { PARENT_COMEDIAN_LINEUP_SELECT } from "@/lib/data/comedian/parentComedianSelect";
import { QueryHelper, SHOW_SORT_MAP } from "@/objects/class/query/QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { computeDistanceMiles } from "@/util/distanceUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { computeShowSoldOut } from "@/util/show/soldOutUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
    zipCapTriggered: boolean;
}

interface ClubShowsOptions {
    page?: string;
    size?: string;
    profileId?: string;
    userId?: string;
}

const SHOW_SELECT = {
    id: true,
    name: true,
    date: true,
    description: true,
    room: true,
    popularity: true,
    tickets: {
        select: {
            price: true,
            soldOut: true,
            purchaseUrl: true,
            type: true,
        },
    },
    club: {
        select: {
            id: true,
            name: true,
            address: true,
            city: true,
            state: true,
            zipCode: true,
            hasImage: true,
            timezone: true,
        },
    },
    lineupItems: {
        where: {
            comedian: {
                visible: true,
                taggedComedians: {
                    none: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        },
        select: {
            role: true,
            comedian: {
                select: {
                    ...LINEUP_COMEDIAN_SELECT,
                    _count: {
                        select: {
                            lineupItems: true,
                        },
                    },
                    parentComedian: {
                        select: {
                            ...PARENT_COMEDIAN_LINEUP_SELECT,
                            _count: {
                                select: {
                                    lineupItems: true,
                                },
                            },
                        },
                    },
                },
            },
        },
    },
    taggedShows: {
        where: { tag: { visibility: "PUBLIC" } },
        select: {
            tag: { select: { slug: true, name: true } },
        },
    },
} as const;

const AVAILABLE_SHOW_WHERE: Prisma.ShowWhereInput = {
    AND: [
        {
            NOT: [
                { name: { contains: "sold out", mode: "insensitive" } },
                { name: { contains: "sold-out", mode: "insensitive" } },
            ],
        },
        {
            OR: [
                { tickets: { none: {} } },
                { tickets: { some: { soldOut: false } } },
            ],
        },
    ],
};

export async function findShowsWithCount(
    helper: QueryHelper,
): Promise<ShowsResponse> {
    try {
        const clubNameClause = helper.getClubNameClause();
        const zipCodeClause = helper.getZipCodeClause();
        // getDateClause returns {} when no fromDate/toDate are set. Show search
        // always wants upcoming-only results, so supply the default here.
        const dateClause = helper.getDateClause();
        const dateFilter =
            "date" in dateClause ? dateClause : { date: { gte: new Date() } };
        const searchWhereClause: Prisma.ShowWhereInput = {
            // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
            ...dateFilter,

            // Club conditions
            club: {
                visible: true,
                // Only add these clauses if they have values
                ...(clubNameClause.name && clubNameClause),
                ...(zipCodeClause.zipCode && zipCodeClause),
            },

            // If the 'comedian' param is provided, it means we're doing a search for shows that contain a specific comedian.
            ...helper.getLineupItemClause(),

            // Match any shows with tags matching the display of the provided filter
            ...helper.getShowTagsClause(),
            ...helper.getShowTypeClause(),

            // Free filter: when the FREE_FILTER_SLUG is in the filters CSV,
            // narrow to shows with at least one ticket priced 0 or NULL.
            ...helper.getFreeShowsClause(),
        };
        const searchAndClauses = Array.isArray(searchWhereClause.AND)
            ? searchWhereClause.AND
            : searchWhereClause.AND
              ? [searchWhereClause.AND]
              : [];
        const whereClause: Prisma.ShowWhereInput = {
            ...searchWhereClause,
            AND: [...searchAndClauses, AVAILABLE_SHOW_WHERE],
        };

        // Sequential awaits instead of a RepeatableRead transaction — slight count/data
        // skew between the two calls is acceptable for paginated search (same pattern
        // as findComediansWithCount and findClubsWithCount). The transaction was
        // crashing on Neon serverless (digest 3246448085).
        const totalCount = await db.show.count({
            where: whereClause,
        });

        const filteredShows = await db.show.findMany({
            where: whereClause,
            select: {
                ...SHOW_SELECT,
                lineupItems: {
                    ...SHOW_SELECT.lineupItems,
                    select: {
                        role: true,
                        comedian: {
                            select: {
                                ...SHOW_SELECT.lineupItems.select.comedian
                                    .select,
                                ...(helper.getProfileId()
                                    ? {
                                          favoriteComedians: {
                                              where: {
                                                  profileId:
                                                      helper.getProfileId(),
                                              },
                                              select: {
                                                  id: true,
                                              },
                                          },
                                      }
                                    : {}),
                            },
                        },
                    },
                },
            },
            ...helper.getGenericClauses(totalCount, SHOW_SORT_MAP, [
                { date: "asc" },
                { id: "asc" },
            ]),
        });
        const availableShows = filteredShows.filter(
            (show) => !computeShowSoldOut(show.name, show.tickets),
        );
        // distanceMiles is null whenever zip is absent (e.g. club detail page, comedian page).
        // Cards hide the distance label when distanceMiles is null — this is intentional.
        const searchedZip = helper.params.zip;
        return {
            zipCapTriggered: helper.isZipCapTriggered(),
            totalCount: Math.max(
                0,
                totalCount - (filteredShows.length - availableShows.length),
            ),
            shows: availableShows.map((show) =>
                mapShowToDTO(show, helper, searchedZip),
            ),
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findShowsWithCount:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while fetching shows");
    }
}

export async function findUpcomingShowsForClub(
    clubId: number,
    options: ClubShowsOptions = {},
): Promise<ShowsResponse> {
    const helper = new QueryHelper({
        params: {
            page: options.page,
            size: options.size,
            sort: SortParamValue.DateAsc,
        },
        timezone: "UTC",
        profileId: options.profileId,
        userId: options.userId,
    });
    const whereClause: Prisma.ShowWhereInput = {
        date: { gte: new Date() },
        club: {
            id: clubId,
            visible: true,
        },
        AND: [AVAILABLE_SHOW_WHERE],
    };

    const totalCount = await db.show.count({ where: whereClause });
    const filteredShows = await db.show.findMany({
        where: whereClause,
        select: {
            ...SHOW_SELECT,
            lineupItems: {
                ...SHOW_SELECT.lineupItems,
                select: {
                    role: true,
                    comedian: {
                        select: {
                            ...SHOW_SELECT.lineupItems.select.comedian.select,
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
                    },
                },
            },
        },
        ...helper.getGenericClauses(totalCount, SHOW_SORT_MAP, [
            { date: "asc" },
            { id: "asc" },
        ]),
    });
    const availableShows = filteredShows.filter(
        (show) => !computeShowSoldOut(show.name, show.tickets),
    );

    return {
        zipCapTriggered: false,
        totalCount: Math.max(
            0,
            totalCount - (filteredShows.length - availableShows.length),
        ),
        shows: availableShows.map((show) => mapShowToDTO(show, helper)),
    };
}

function mapShowToDTO(
    show: Prisma.ShowGetPayload<{ select: typeof SHOW_SELECT }>,
    helper: QueryHelper,
    searchedZip?: string,
): ShowDTO {
    return {
        id: show.id,
        date: show.date,
        name: show.name,
        description: show.description ?? undefined,
        room: show.room,
        address: show.club.address,
        clubId: show.club.id,
        clubName: show.club.name,
        clubCity: show.club.city,
        clubState: show.club.state,
        imageUrl: buildClubImageUrl(show.club.name, show.club.hasImage),
        soldOut: computeShowSoldOut(show.name, show.tickets),
        lineup: filterAndMapLineupItems(show.lineupItems, helper.getUserId()),
        tickets: mapTickets(show.tickets),
        distanceMiles: computeDistanceMiles(searchedZip, show.club.zipCode),
        timezone: show.club.timezone,
        tags: (show.taggedShows ?? [])
            .map((tt) => tt.tag)
            .filter(
                (tag): tag is { slug: string; name: string } =>
                    typeof tag?.slug === "string" &&
                    typeof tag?.name === "string",
            )
            .map((tag) => ({ slug: tag.slug, name: tag.name })),
    };
}
