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
        const filters = await getFilters(EntityType.Comedian, providedFilters == null ? undefined : providedFilters)

        const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

        return getClubDetailPageData(helper.asQueryFilters())
            .then((response: ClubDetailResponse) => NextResponse.json({ data: response.data, shows: response.shows, total: response.total, filters: filters }, { status: 200 }))
            .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
    } catch (e) {
        console.log(e)
    }
}
