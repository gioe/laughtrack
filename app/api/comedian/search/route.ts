/* eslint-disable @typescript-eslint/no-explicit-any */

import { getTags } from "@/lib/data/tags/get";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { NextResponse } from "next/server";
import { ComedianSearchData, ComedianSearchDTO } from "./interface";
import { getSearchedComedians } from "@/lib/data/comedian/search/get";

export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Comedian);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedComedians(helper.asQueryFilters())
        .then((response: ComedianSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ComedianDTO) => new Comedian(result)),
                total: response.response.total,
            } as ComedianSearchData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
