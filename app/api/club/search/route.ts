/* eslint-disable @typescript-eslint/no-explicit-any */

import { db } from "@/lib/db";
import { ClubSearchData, ClubSearchDTO } from "./interface";
import { getTags } from "@/lib/data/tags/get";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import { NextResponse } from "next/server";

async function getFilteredClubs(params: any): Promise<ClubSearchDTO> {
    const totalCount = await db.club.count({
        where: {
            name: {
                contains: params.query,
                mode: 'insensitive'
            },
            ...(!params.tagsEmpty ? {
                taggedClubs: {
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

    // Get filtered data
    const clubs = await db.club.findMany({
        select: {
            id: true,
            name: true,
            address: true,
            website: true
        },
        where: {
            name: {
                contains: params.query,
                mode: 'insensitive'
            },
            ...(!params.tagsEmpty ? {
                taggedClubs: {
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
    });

    return {
        response: {
            data: clubs,
            total: totalCount
        }
    };
}

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Club);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getFilteredClubs(helper.asQueryFilters())
        .then((response: ClubSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ClubDTO) => new Club(result)),
                total: response.response.total
            } as ClubSearchData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
