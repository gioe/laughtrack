import { db } from "@/lib/db"
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
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

            // If the 'city' param is provided, this means we only want shows from clubs in a specific city.
            ...(city ? {
                city: {
                    name: city
                }
            } : {}),
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
        // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
        date: {
            gte: from_date ? new Date(from_date).toISOString() : new Date().toISOString(),
            // If a Less Than (lte) paramater is provided, include that.
            ...(to_date ? { lte: new Date(to_date).toISOString() } : {})
        },
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

    console.log(whereClause)
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
                                parentComedian: true,
                                alternativeNames: {
                                    select: {
                                        id: true
                                    }
                                },
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

const filterAndMapLineupItems = (lineupItems: any[], userId?: number) => {
    console.log(lineupItems)
    // First, create a set of parent IDs that are present in the lineup
    const parentIdsInLineup = new Set(
        lineupItems
            .flatMap(comedian => {
                if (comedian.parendComedian == undefined) {
                    return comedian.id
                }
            })
    );

    // Filter out children whose parents are in the lineup
    const filteredItems = lineupItems.filter(item => {
        const hasParent = !!item.comedian.parentComedian;
        if (!hasParent) return true; // Keep all non-child comedians

        // Keep child only if their parent is not in the lineup
        return !parentIdsInLineup.has(item.comedian.parentComedian.id);
    });

    // Map the filtered items
    return filteredItems.map(item => mapLineupItem(item, userId));
};

const mapLineupItem = (item: { comedian: any }, userId?: number) => {
    const effectiveComedian = getEffectiveComedian(item.comedian);

    return {
        id: effectiveComedian.id,
        uuid: effectiveComedian.uuid,
        name: effectiveComedian.name,
        imageUrl: buildComedianImageUrl(effectiveComedian.name),
        isFavorite: userId ? item.comedian.favoriteComedians.length > 0 : false,
        isAlias: item.comedian.taggedComedians.length > 0
    };
};

const getEffectiveComedian = (comedian: any) => comedian.parentComedian || comedian;
