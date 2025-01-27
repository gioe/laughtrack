import { QueryProperty } from "@/objects/enum";
import { ClubDetailResponse } from "./interface";
import { NextResponse } from "next/server";
import { getClubDetailPageData } from "@/lib/data/club/getClubDetailPageData";
import { headers } from "next/headers";

export async function GET(request: Request, { params }) {
    try {

        const slug = await params
        const headersList = await headers();

        const searchParams = new URL(request.url).searchParams
        const providedFilters = searchParams.get(QueryProperty.Filters)

        return getClubDetailPageData(searchParams, headersList, slug, providedFilters == null ? undefined : providedFilters)
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
