/* eslint-disable @typescript-eslint/no-explicit-any */

import { db } from "@/lib/db";
import { ClubSearchData, ClubSearchDTO } from "./interface";
import { getTags } from "@/lib/data/tags/getTags";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import { NextResponse } from "next/server";
import { getSearchedClubs } from "@/lib/data/club/getSearchedClubs";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Club);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedClubs(helper.asQueryFilters())
        .then((response: ClubSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ClubDTO) => new Club(result)),
                total: response.response.total
            } as ClubSearchData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
