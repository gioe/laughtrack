import { db } from "@/lib/db"
import { ShowDTO } from "@/objects/class/show/show.interface"
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
        city,
        filters,
        filtersEmpty,
        direction,
        size,
        offset,
        sortBy,
    } = params

    // Common where clause for both count and find
    const whereClause = {
        ...(club ? {
            club: {
                name: {
                    contains: club,
                    mode: Prisma.QueryMode.insensitive,
                },
                visible: true,
                ...(city ? {
                    city: {
                        name: city
                    }
                } : {}),
            },

        } : {}),
        ...(comedian ?
            {
                lineupItems: {
                    some: {
                        comedian: {
                            name: {
                                contains: comedian,
                                mode: Prisma.QueryMode.insensitive,
                            },
                        },
                    },
                },
            } : {}),
        date: {
            gte: from_date ? new Date(from_date).toISOString() : new Date().toISOString(),
            ...(to_date ? { lte: new Date(to_date).toISOString() } : {})
        },
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

    // Execute both queries in parallel
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
            lineup: show.lineupItems.map(item => ({
                id: item.comedian.id,
                uuid: item.comedian.uuid,
                name: item.comedian.name,
                imageUrl: buildComedianImageUrl(item.comedian.name),
                isFavorite: userId ? item.comedian.favoriteComedians.length > 0 : false,
                isAlias: item.comedian.taggedComedians.length > 0
            }))
        })),
        totalCount
    }
}
