/* eslint-disable @typescript-eslint/no-explicit-any */


import { NextResponse } from "next/server";
import { db } from "../../../lib/db";
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ComedianDetailDTO, ComedianDetailPageData } from "../../../(entities)/(detail)/comedian/[name]/interface";
import { getTags } from "../../show/search/route";
import { Comedian } from "../../../../objects/class/comedian/Comedian";

async function getComedianDetailPageData(params: any) {

    // First get all relevant shows
    const relevantShows = await db.show.findMany({
        where: {
            date: {
                gt: new Date()
            },
            lineupItems: {
                some: {
                    comedian: {
                        name: params.name
                    }
                }
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
            id: true
        },
        orderBy: {
            [params.sortBy]: params.direction.toLowerCase()
        },
        take: Number(params.size),
        skip: params.offset
    });

    const showIds = relevantShows.map(show => show.id);

    // Get detailed show data
    const showData = await db.show.findMany({
        where: {
            id: {
                in: showIds
            }
        },
        select: {
            id: true,
            name: true,
            date: true,
            lastScrapedDate: true,
            ticketPrice: true,
            ticketPurchaseUrl: true,
            lineupItems: {
                select: {
                    comedian: {
                        select: {
                            id: true,
                            name: true
                        }
                    }
                }
            },
            club: {
                select: {
                    name: true
                }
            }
        },
        orderBy: {
            [params.sortBy]: params.direction.toLowerCase()
        }
    });

    // Get total count
    const totalCount = await db.show.count({
        where: {
            date: {
                gt: new Date()
            },
            lineupItems: {
                some: {
                    comedian: {
                        name: params.name
                    }
                }
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

    // Get comedian data
    const comedianData = await db.comedian.findFirst({
        where: {
            name: params.name
        },
        select: {
            id: true,
            name: true,
            linktree: true,
            instagramAccount: true,
            instagramFollowers: true,
            tiktokAccount: true,
            tiktokFollowers: true,
            youtubeAccount: true,
            youtubeFollowers: true,
            website: true,
            popularity: true
        }
    });

    if (!comedianData) {
        throw new Error(`Comedian with name ${name} not found`);
    }

    // Format the response
    const formattedShows = showData.map(show => ({
        id: show.id,
        date: show.date,
        name: show.name,
        ticket: {
            price: show.ticketPrice,
            link: show.ticketPurchaseUrl
        },
        club_name: show.club.name,
        scrapedate: show.lastScrapedDate,
        lineup: show.lineupItems.map(item => ({
            id: item.comedian.id,
            name: item.comedian.name
        }))
    }));

    return {
        response: {
            data: {
                name: comedianData.name,
                id: comedianData.id,
                social_data: {
                    id: comedianData.id,
                    linktree: comedianData.linktree,
                    instagram_account: comedianData.instagramAccount,
                    instagram_followers: comedianData.instagramFollowers,
                    tiktok_account: comedianData.tiktokAccount,
                    tiktok_followers: comedianData.tiktokFollowers,
                    youtube_account: comedianData.youtubeAccount,
                    youtube_followers: comedianData.youtubeFollowers,
                    website: comedianData.website,
                    popularity: comedianData.popularity
                },
                dates: formattedShows
            },
            total: totalCount
        }
    }
}

export async function GET(request: Request, { params }) {
    const slug = await params

    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

    return getComedianDetailPageData(helper.asQueryFilters())
        .then((response: ComedianDetailDTO) => {
            const data = {
                entity: new Comedian(response.response.data),
                total: response.response.total
            } as ComedianDetailPageData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
