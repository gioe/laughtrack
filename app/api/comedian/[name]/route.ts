/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/getTags";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { ComedianDetailDTO, ComedianDetailPageData } from "./interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { NextResponse } from "next/server";
import { getComedianDetailPageData } from "@/lib/data/comedian/getComedianDetailPageData";


export async function GET(request: Request, { params }) {
    const slug = await params

    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

    return getComedianDetailPageData(helper.asQueryFilters())
        .then((response: ComedianDetailDTO) => {
            const data = {
                entity: new Comedian(response.response.data),
                total: response.response.total
            } as ComedianDetailPageData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
