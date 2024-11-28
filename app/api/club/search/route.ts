
import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ClubSearchData } from "../../../(entities)/(collection)/club/all/interface";
const { database } = getDB();

export async function GET(request: Request) {
    const searchParams = new URL(request.url).searchParams
    const filters = await database.queries.getTags([EntityType.Club]);

    const helper = await QueryHelper.storePageParams(searchParams, filters);

    return database.page.getClubSearchPageData(helper.asQueryFilters())
        .then((data: ClubSearchData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
