/* eslint-disable @typescript-eslint/no-explicit-any */

import { QueryProperty } from "@/objects/enum";
import { ComedianDetailResponse } from "./interface";
import { NextResponse } from "next/server";
import { getComedianDetailPageData } from "@/lib/data/comedian/getComedianDetailPageData";
import { headers } from "next/headers";

export async function GET(request: Request, { params }) {
    const headersList = await headers();
    const slug = await params

    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const providedFilters = searchParams.get(QueryProperty.Filters)

    return getComedianDetailPageData(searchParams, slug, headersList, providedFilters == null ? undefined : providedFilters)
        .then((response: ComedianDetailResponse) => NextResponse.json({
            data: response.data,
            shows: response.shows,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
