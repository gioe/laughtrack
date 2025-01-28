import { QueryProperty } from "@/objects/enum";
import { NextResponse } from "next/server";
import { getSearchedClubs } from "@/lib/data/club/getSearchedClubs";
import { ClubSearchResponse } from "./interface";
import { headers } from "next/headers";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const headersList = await headers();

    const providedFilters = searchParams.get(QueryProperty.Filters)

    return getSearchedClubs(searchParams, headersList, providedFilters == null ? undefined : providedFilters)
        .then((response: ClubSearchResponse) => NextResponse.json({
            data: response.data,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
