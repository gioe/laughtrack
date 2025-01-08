/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextResponse } from "next/server";
import { db } from "../../../lib/db";
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ComedianSearchData, ComedianSearchDTO } from "../../../(entities)/(collection)/comedian/all/interface";
import { getTags } from "../../show/search/route";
import { ComedianDTO } from "../../../../objects/class/comedian/comedian.interface";
import { Comedian } from "../../../../objects/class/comedian/Comedian";

async function getFilteredComedians(params: any): Promise<ComedianSearchDTO> {
    // First get total count
    const totalCount = await db.comedian.count({
        where: {
            name: {
                contains: params.query,
                mode: 'insensitive'
            },
            ...(!params.tagsEmpty ? {
                taggedComedians: {
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

    // Then get filtered data
    const comedians = await db.comedian.findMany({
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
        },
        where: {
            name: {
                contains: params.query,
                mode: 'insensitive'
            },
            ...(!params.tagsEmpty ? {
                taggedComedians: {
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
    const formattedData = comedians.map(comedian => ({
        id: comedian.id,
        name: comedian.name,
        social_data: {
            id: comedian.id,
            linktree: comedian.linktree,
            instagram_account: comedian.instagramAccount,
            instagram_followers: comedian.instagramFollowers,
            tiktok_account: comedian.tiktokAccount,
            tiktok_followers: comedian.tiktokFollowers,
            youtube_account: comedian.youtubeAccount,
            youtube_followers: comedian.youtubeFollowers,
            website: comedian.website,
            popularity: comedian.popularity
        }
    }))

    return {
        response: {
            data: formattedData,
            total: totalCount
        }
    }
}


export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Comedian);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getFilteredComedians(helper.asQueryFilters())
        .then((response: ComedianSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ComedianDTO) => new Comedian(result)),
                total: response.response.total
            } as ComedianSearchData
            return NextResponse.json({ data }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
