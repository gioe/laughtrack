/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/getTags";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedComedians } from "@/lib/data/comedian/getSearchedComedians";
import { ComedianSearchResponse } from "./interface";

export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Comedian);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedComedians(helper.asQueryFilters())
        .then((response: ComedianSearchResponse) => {
            return NextResponse.json({ response }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
