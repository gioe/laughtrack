import { getFilters } from "@/lib/data/filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { NextResponse } from "next/server";
import { getSearchedClubs } from "@/lib/data/club/getSearchedClubs";
import { ClubSearchResponse } from "./interface";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const providedFilters = searchParams.get(QueryProperty.Filters)

    return getSearchedClubs(searchParams, providedFilters == null ? undefined : providedFilters)
        .then((response: ClubSearchResponse) => NextResponse.json({
            data: response.data,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
