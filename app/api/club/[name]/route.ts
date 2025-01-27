import { getFilters } from "@/lib/data/filters/getFilters";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType, QueryProperty } from "@/objects/enum";
import { ClubDetailResponse } from "./interface";
import { NextResponse } from "next/server";
import { getClubDetailPageData } from "@/lib/data/club/getClubDetailPageData";

export async function GET(request: Request, { params }) {
    try {

        const slug = await params
        const searchParams = new URL(request.url).searchParams
        const providedFilters = searchParams.get(QueryProperty.Filters)

        return getClubDetailPageData(searchParams, slug, providedFilters == null ? undefined : providedFilters)
            .then((response: ClubDetailResponse) => NextResponse.json({
                data: response.data,
                shows: response.shows,
                total: response.total,
                filters: response.filters
            }, { status: 200 }))
            .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
    } catch (e) {
        console.log(e)
    }
}
