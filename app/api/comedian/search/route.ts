import { QueryProperty } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedComedians } from "@/lib/data/comedian/getSearchedComedians";
import { ComedianSearchResponse } from "./interface";

export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const providedFilters = searchParams.get(QueryProperty.Filters)

    return getSearchedComedians(searchParams, providedFilters == null ? undefined : providedFilters)
        .then((response: ComedianSearchResponse) => NextResponse.json({
            data: response.data,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
