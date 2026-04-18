import { db } from "@/lib/db";
import { QueryHelper, SHOW_SORT_MAP } from "@/objects/class/query/QueryHelper";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { computeDistanceMiles } from "@/util/distanceUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
    zipCapTriggered: boolean;
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
            name: true,
            address: true,
            zipCode: true,
            hasImage: true,
            timezone: true,
        },
    },
    lineupItems: {
        where: {
            comedian: {
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
            comedian: {
                select: {
                    id: true,
                    uuid: true,
                    name: true,
                    hasImage: true,
                    parentComedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            hasImage: true,
                            taggedComedians: {
                                select: {
                                    tag: true,
                                },
                            },
                        },
                    },
                    taggedComedians: {
                        select: {
                            tag: true,
                        },
                    },
                },
            },
        },
    },
} as const;

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
            "date" in dateClause
                ? dateClause
                : { date: { gte: new Date() } };
        const whereClause: Prisma.ShowWhereInput = {
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
        // distanceMiles is null whenever zip is absent (e.g. club detail page, comedian page).
        // Cards hide the distance label when distanceMiles is null — this is intentional.
        const searchedZip = helper.params.zip;
        return {
            zipCapTriggered: helper.isZipCapTriggered(),
            shows: filteredShows.map((show) => ({
                id: show.id,
                date: show.date,
                name: show.name,
                description: show.description ?? undefined,
                room: show.room,
                address: show.club.address,
                clubName: show.club.name,
                imageUrl: buildClubImageUrl(show.club.name, show.club.hasImage),
                soldOut:
                    show.tickets.length > 0 &&
                    show.tickets.every((t) => t.soldOut === true),
                lineup: filterAndMapLineupItems(
                    show.lineupItems,
                    helper.getUserId(),
                ),
                tickets: mapTickets(show.tickets),
                distanceMiles: computeDistanceMiles(
                    searchedZip,
                    show.club.zipCode,
                ),
                timezone: show.club.timezone,
            })),
            totalCount,
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findShowsWithCount:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while fetching shows");
    }
}
