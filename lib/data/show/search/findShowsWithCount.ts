import { db } from "@/lib/db"
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ShowDTO } from "@/objects/class/show/show.interface"
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl } from "@/util/imageUtil"
import { mapTickets } from "@/util/ticket/ticketUtil";

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
}

export async function findShowsWithCount(helper: QueryHelper): Promise<ShowsResponse> {
    const whereClause = {
        // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
        ...helper.getDateClause(),
        // Every show search has limitations on the club, even if it's just clubs in a as specific city.
        club: {
            // Only visible clubs included.
            visible: true,

            // If the 'club' param is provided, this means there is a club name query string so we need to match on that.
            ...helper.getClubNameClause(),

            // If the 'zip_codes' param is provided, this means we only want shows from clubs in a specific zip codes.
            ...helper.getZipCodeClause()
        },
        // If the 'comedian' param is provided, it means we're doing a search for shows that contain a specific comedian.
        // This is not always provided. Sometimes the other clauses are sufficient for a lookup.
        ...helper.getLineupItemClause(),
        // Match any shows with tags matching the display of the provided filter, if the filter values aren't empty
        ...helper.getShowFiltersClause(),
    }

    const totalCount = await db.show.count({
        where: whereClause
    })

    // Execute both queries in parallel, one to get the shows and the other to get the count.
    const filteredShows = await
        db.show.findMany({
            where: whereClause,
            select: {
                id: true,
                name: true,
                date: true,
                lastScrapedDate: true,
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
                    select: {
                        comedian: {
                            select: {
                                id: true,
                                uuid: true,
                                name: true,
                                // We'll need to understand if the comedian is a parent for downstream processing
                                parentComedian: true,
                                // We may
                                taggedComedians: {
                                    where: {
                                        tag: {
                                            value: 'alias'
                                        }
                                    },
                                    select: {
                                        id: true
                                    }
                                },
                                ...helper.getFavoriteComedianClauseWithSelection()
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
            scrapedate: show.lastScrapedDate,
            lineup: filterAndMapLineupItems(show.lineupItems, helper.getUserId()),
            tickets: mapTickets(show.tickets),
        })),
        totalCount
    }
}
