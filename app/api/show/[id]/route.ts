export const dynamic = 'force-static'

import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ShowDetailPageData } from "../../../(entities)/(detail)/show/[name]/interface";
const { database } = getDB();

export async function GET(request: Request, { params }) {
    const slug = await params
    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await database.queries.getTags([EntityType.Comedian]);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

    return database.page.getShowDetailPageData(helper.asQueryFilters())
        .then((data: ShowDetailPageData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
