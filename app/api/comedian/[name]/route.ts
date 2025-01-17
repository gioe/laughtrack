/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/getTags";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { ComedianDetailResponse } from "./interface";
import { NextResponse } from "next/server";
import { getComedianDetailPageData } from "@/lib/data/comedian/getComedianDetailPageData";


export async function GET(request: Request, { params }) {
    const slug = await params

    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

    return getComedianDetailPageData(helper.asQueryFilters())
        .then((response: ComedianDetailResponse) => NextResponse.json({ response }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
