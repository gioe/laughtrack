/* eslint-disable @typescript-eslint/no-explicit-any */
import { getTags } from "@/lib/data/tags/get";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityType } from "@/objects/enum";
import { NextResponse } from "next/server";
import { ShowSearchData, ShowSearchDTO } from "./interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Show } from "@/objects/class/show/Show";
import { getSearchedShows } from "@/lib/data/show/search/get";

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await getTags(EntityType.Show);
    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return getSearchedShows(helper.asQueryFilters())
        .then((response: ShowSearchDTO) => {
            const data = {
                entities: response.response.data.map((result: ShowDTO) => new Show(result)),
                total: response.response.total
            } as ShowSearchData
            return NextResponse.json({ data, filters }, { status: 200 })
        })
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
