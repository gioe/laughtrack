import { db } from "@/lib/db"
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ShowDTO } from "@/objects/class/show/show.interface"
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl } from "@/util/imageUtil"
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
}

const SHOW_SELECT = {
    id: true,
    name: true,
    date: true,
    popularity: true,
    tickets: {
        select: {
            price: true,
            soldOut: true,
            purchaseUrl: true,
            type: true
        }
    },
    club: {
        select: {
            name: true,
            address: true
        }
    },
    lineupItems: {
        where: {
            comedian: {
                taggedComedians: {
                    none: {
                        tag: {
                            userFacing: false
                        }
                    }
                }
            }
        },
        select: {
            comedian: {
                select: {
                    id: true,
                    uuid: true,
                    name: true,
                    parentComedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            taggedComedians: {
                                select: {
                                    tag: true
                                }
                            }
                        }
                    },
                    taggedComedians: {
                        select: {
                            tag: true
                        }
                    }
                }
            }
        }
    }
} as const;

export async function findShowsWithCount(helper: QueryHelper): Promise<ShowsResponse> {
    try {
        const whereClause: Prisma.ShowWhereInput = {
            // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
            ...helper.getDateClause(),

            // Club conditions
            club: {
                visible: true,
                // Only add these clauses if they have values
                ...(helper.getClubNameClause().name && helper.getClubNameClause()),
                ...(helper.getZipCodeClause().zipCode && helper.getZipCodeClause())
            },

            // If the 'comedian' param is provided, it means we're doing a search for shows that contain a specific comedian.
            ...helper.getLineupItemClause(),

            // Match any shows with tags matching the display of the provided filter
            ...helper.getShowTagsClause(),
        };


        // Get total count first
        const totalCount = await db.show.count({
            where: whereClause
        });

        // Then get filtered shows with pagination
        const filteredShows = await db.show.findMany({
            where: whereClause,
            select: {
                ...SHOW_SELECT,
                lineupItems: {
                    ...SHOW_SELECT.lineupItems,
                    select: {
                        comedian: {
                            select: {
                                ...SHOW_SELECT.lineupItems.select.comedian.select,
                                ...(helper.getProfileId() ? {
                                    favoriteComedians: {
                                        where: {
                                            profileId: helper.getProfileId()
                                        },
                                        select: {
                                            id: true
                                        }
                                    }
                                } : {})
                            }
                        }
                    }
                }
            },
            ...helper.getGenericClauses(totalCount),
        });
        return {
            shows: filteredShows.map(show => ({
                id: show.id,
                date: show.date,
                name: show.name,
                address: show.club.address,
                clubName: show.club.name,
                imageUrl: buildClubImageUrl(show.club.name),
                lineup: filterAndMapLineupItems(show.lineupItems, helper.getUserId()),
                tickets: mapTickets(show.tickets),
            })),
            totalCount
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error('Error in findShowsWithCount:', error);
            throw error;
        }
        throw new Error('An unknown error occurred while fetching shows');
    }
}
