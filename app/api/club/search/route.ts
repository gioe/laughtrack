/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/getTags";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { NextResponse } from "next/server";
import { getSearchedClubs } from "@/lib/data/club/getSearchedClubs";
import { ClubSearchResponse } from "./interface";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Club);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedClubs(helper.asQueryFilters())
        .then((response: ClubSearchResponse) => NextResponse.json({ data: response.data, total: response.total }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
