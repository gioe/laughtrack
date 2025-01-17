/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/getTags";
import { Club } from "@/objects/class/club/Club";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { ClubDetailDTO, ClubDetailPageData } from "./interface";
import { NextResponse } from "next/server";
import { getClubDetailPageData } from "@/lib/data/club/getClubDetailPageData";


export async function GET(request: Request, { params }) {
    try {

        const slug = await params
        const newURL = new URL(request.url);
        const searchParams = newURL.searchParams
        const filters = await getTags(EntityType.Comedian);

        const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

        return getClubDetailPageData(helper.asQueryFilters())
            .then((response: ClubDetailDTO) => {
                const data = {
                    entity: new Club(response.response.data),
                    total: response.response.total
                } as ClubDetailPageData
                return NextResponse.json({ data, filters }, { status: 200 })
            })
            .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
    } catch (e) {
        console.log(e)
    }
}
