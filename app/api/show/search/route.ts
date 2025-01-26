import { getFilters } from "@/lib/data/filters/getFilters";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType, QueryProperty } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/getSearchedShows";
import { ShowSearchResponse } from "./interface";

export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const providedFilters = searchParams.get(QueryProperty.Filters)
    const filters = await getFilters(EntityType.Show, providedFilters == null ? undefined : providedFilters)

    const helper = await QueryHelper.storePageParams(searchParams, filters);

    console.log(helper.asQueryFilters())

    return getSearchedShows(helper.asQueryFilters())
        .then((response: ShowSearchResponse) => NextResponse.json({ data: response.data, total: response.total, filters: filters }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
