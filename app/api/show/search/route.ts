import { QueryProperty } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/getSearchedShows";
import { ShowSearchResponse } from "./interface";
import { headers } from "next/headers";

export async function GET(request: Request) {
    const headersList = await headers();

    const searchParams = new URL(request.url).searchParams
    const providedFilters = searchParams.get(QueryProperty.Filters)

    return getSearchedShows(searchParams, headersList, providedFilters == null ? undefined : providedFilters)
        .then((response: ShowSearchResponse) => NextResponse.json({
            data: response.data,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
