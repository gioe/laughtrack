/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextResponse } from "next/server";
import { db } from "../../../lib/db";
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ClubDetailPageData } from "../../../(entities)/(detail)/club/[name]/interface";
import { headers } from "next/headers";
import { getTags } from "../../show/search/route";
import { Club } from "../../../../objects/class/club/Club";

async function getClubDetailPageData(params: any) {
    // Get filtered shows with basic info
    const filteredShows = await db.show.findMany({
        where: {
            club: {
                name: params.name
            },
            date: {
                gt: new Date()
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
        select: {
            id: true,
            name: true,
            lastScrapedDate: true,
            date: true,
            popularity: true,
            ticketPrice: true,
            ticketPurchaseUrl: true,
            club: {
                select: {
                    id: true,
                    name: true,
                    website: true,
                    city: true,
                    address: true,
                    zipCode: true
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
                                take: 1
                            },
                            ...(params.userId && {
                                favoriteComedians: {
                                    where: {
                                        userId: Number(params.userId)
                                    },
                                    take: 1
                                }
                            })
                        }
                    }
                }
            }
        },
        orderBy: {
            [params.sortBy]: params.direction.toLowerCase()
        },
        take: Number(params.size),
        skip: params.offset
    });

    // Get total count
    const totalCount = await db.show.count({
        where: {
            club: {
                name: params.name
            },
            date: {
                gt: new Date()
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
    });

    // Get club data
    const clubData = await db.club.findFirst({
        where: {
            name: params.clubName
        },
        select: {
            id: true,
            name: true,
            website: true,
            city: true,
            address: true,
            zipCode: true
        }
    });

    if (!clubData) {
        throw new Error(`Club with name ${params.clubName} not found`);
    }
    // Format the shows data
    const formattedShows = filteredShows.map((show) => {
        return {
            id: show.id,
            date: show.date,
            name: show.name,
            ticket: {
                price: show.ticketPrice,
                link: show.ticketPurchaseUrl
            },
            club_name: show.club.name,
            scrapedate: show.lastScrapedDate,
            lineup: show.lineupItems.map((item) => {
                return {
                    id: item.comedian.id,
                    name: item.comedian.name,
                    is_favorite: params.userId ? item.comedian.favoriteComedians.length > 0 : false,
                    is_alias: item.comedian.taggedComedians.length > 0
                }
            })
        }
    })

    return {
        response: {
            data: {
                name: clubData.name,
                id: clubData.id,
                website: clubData.website,
                city: clubData.city,
                address: clubData.address,
                zipCode: clubData.zipCode,
                dates: formattedShows
            },
            total: totalCount
        }
    };
}

export async function GET(request: Request, { params }) {
    const headersList = await headers();
    const userId = headersList.get("user_id");

    const slug = await params
    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug, userId);

    return getClubDetailPageData(helper.asQueryFilters())
        .then((response: any) => {
            const data = {
                entity: new Club(response.response.data),
                total: response.response.total
            } as ClubDetailPageData
            console.log(data)
            return NextResponse.json({ data }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
