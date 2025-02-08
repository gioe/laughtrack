import { db } from "@/lib/db"
import { ShowDTO } from "@/objects/class/show/show.interface"
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl, buildComedianImageUrl } from "@/util/imageUtil"
import { Prisma } from "@prisma/client";

const EXCLUSIVITY_TAGS = ['Not Even Funny']

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
}

export async function findShowsWithCount(params: any): Promise<ShowsResponse> {
    const {
        userId,
        from_date,
        club,
        comedian,
        to_date,
        zip_codes,
        filters,
        filtersEmpty,
        direction,
        size,
        offset,
        sortBy,
    } = params

    const whereClause = {
        // Every show search has limitations on the club, even if it's just clubs in a as specific city.
        club: {
            // Only visible clubs included.
            visible: true,

            // If the 'club' param is provided, this means there is a club name query string so we need to match on that.
            ...(club ? {
                name: {
                    contains: club,
                    mode: Prisma.QueryMode.insensitive,
                },
            }: {} ),

            // If the 'zip_codes' param is provided, this means we only want shows from clubs in a specific zip codes.
            ...(zip_codes ? {
                zipCode: {
                    in: zip_codes
                }
            } : {}),
        },
        // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
        date: {
                gte: from_date ? new Date(from_date).toISOString() : new Date().toISOString(),
                // If a Less Than (lte) paramater is provided, include that.
                ...(to_date ? { lte: new Date(to_date).toISOString() } : {})
        },
        // If the 'comedian' param is provided, it means we're doing a search for shows that contain a specific comedian.
        // This is not always provided. Sometimes the other clauses are sufficient for a lookup.
        ...(comedian ? {
            // Lineup items represent shows where the comedian is on the lineup.
            // For every comedian query, we want to return to possibilities:
            lineupItems: {
                some: {
                    comedian: {
                        OR: [
                            // The comedian in the lineup item matches the supplieed query param and has no parent (meaning it is the parent)
                            {
                                name: {
                                    contains: comedian,
                                    mode: Prisma.QueryMode.insensitive,
                                },
                                parentComedianId: null
                            },
                            // OR the comedian in the lineup's parent matches the query param.
                            {
                                parentComedian: {
                                    name: {
                                        contains: comedian,
                                        mode: Prisma.QueryMode.insensitive,
                                    }
                                }
                            }
                        ]
                    },
                },
            },
        } : {}),
        // Match any shows with tags matching the display of the provided filter, if the filter values aren't empty
        ...(!filtersEmpty ? {
            taggedShows: {
                some: {
                    tag: {
                        display: {
                            in: filters
                        }
                    }
                }
            }
        } : {}),
        // Always exclude shows with specific tags. We should make this more scalable.
        NOT: {
            taggedShows: {
                some: {
                    tag: {
                        display: {
                            in: EXCLUSIVITY_TAGS,
                        },
                    },
                },
            },
        },
    }

    // Execute both queries in parallel, one to get the shows and the other to get the count.
    const [filteredShows, totalCount] = await Promise.all([
        db.show.findMany({
            where: whereClause,
            select: {
                id: true,
                name: true,
                date: true,
                lastScrapedDate: true,
                popularity: true,
                ticketPrice: true,
                ticketPurchaseUrl: true,
                soldOut: true,
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
                                ...(userId ? {
                                    favoriteComedians: {
                                        where: {
                                            userId: Number(userId)
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
            orderBy: {
                [sortBy]: direction
            },
            take: Number(size),
            skip: offset,
        }),
        db.show.count({
            where: whereClause
        })
    ])

    return {
        shows: filteredShows.map(show => ({
            id: show.id,
            date: show.date,
            name: show.name,
            ticket: {
                price: show.ticketPrice,
                link: show.ticketPurchaseUrl
            },
            address: show.club.address,
            clubName: show.club.name,
            imageUrl: buildClubImageUrl(show.club.name),
            scrapedate: show.lastScrapedDate,
            soldOut: show.soldOut,
            lineup: filterAndMapLineupItems(show.lineupItems, userId)
        })),
        totalCount
    }
}
