import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ShowSearchData } from "../../../(entities)/(collection)/show/all/interface";
const { database } = getDB();

export async function GET(request: Request) {

    const searchParams = new URL(request.url).searchParams
    const filters = await database.queries.getTags([EntityType.Show]);

    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return database.page.getShowSearchPageData(helper.asQueryFilters())
        .then((data: ShowSearchData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
