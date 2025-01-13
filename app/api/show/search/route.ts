/* eslint-disable @typescript-eslint/no-explicit-any */
import { getTags } from "@/lib/data/tags/get";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { NextResponse } from "next/server";
import { ShowSearchData, ShowSearchDTO } from "./interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Show } from "@/objects/class/show/Show";

async function getFilteredShows(params: any) {
    // Get total count first
    const totalCount = await db.show.count({
        where: {
            club: {
                city: {
                    name: params.city
                }
            },
            date: {
                gte: new Date(params.from_date).toISOString(),
                lte: new Date(params.to_date).toISOString(),
            },
            ...(!params.tagsEmpty ? {
                taggedShows: {
                    some: {
                        tag: {
                            value: {
                                in: params.tags
                            }
                        }
                    }
                }
            } : {})
        }
    })

    // Get filtered shows with related data
    const shows = await db.show.findMany({
        select: {
            id: true,
            name: true,
            date: true,
            lastScrapedDate: true,
            popularity: true,
            ticketPrice: true,
            ticketPurchaseUrl: true,
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
                            ...(params.userId ? {
                                favoriteComedians: {
                                    where: {
                                        userId: Number(params.userId)
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
        where: {
            club: {
                city: {
                    name: params.city
                }
            },
            date: {
                gte: new Date(params.from_date).toISOString(),
                lte: new Date(params.to_date).toISOString(),
            },
            ...(!params.tagsEmpty ? {
                taggedShows: {
                    some: {
                        tag: {
                            value: {
                                in: params.tags
                            }
                        }
                    }
                }
            } : {})
        },
        orderBy: {
            [params.sortBy]: params.direction
        },
        take: Number(params.size),
        skip: params.offset
    })

    // Transform the data to match the original SQL output structure
    const formattedShows = shows.map(show => ({
        id: show.id,
        date: show.date,
        name: show.name,
        ticket: {
            price: show.ticketPrice,
            link: show.ticketPurchaseUrl
        },
        club_address: show.club.address,
        club_name: show.club.name,
        scrapedate: show.lastScrapedDate,
        lineup: show.lineupItems.map(item => ({
            id: item.comedian.id,
            name: item.comedian.name,
            is_favorite: params.userId ? item.comedian.favoriteComedians.length > 0 : false,
            is_alias: item.comedian.taggedComedians.length > 0
        }))
    }))

    return {
        response: {
            data: formattedShows,
            total: totalCount
        }
    }
}

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Show);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getFilteredShows(helper.asQueryFilters())
        .then((response: ShowSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ShowDTO) => new Show(result)),
                total: response.response.total
            } as ShowSearchData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
