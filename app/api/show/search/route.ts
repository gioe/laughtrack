/* eslint-disable @typescript-eslint/no-explicit-any */
import { getTags } from "@/lib/data/tags/getTags";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/getSearchedShows";
import { ShowSearchResponse } from "./interface";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Show);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedShows(helper.asQueryFilters())
        .then((response: ShowSearchResponse) => NextResponse.json({ data: response.data, total: response.total }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
