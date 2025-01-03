
import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
const { database } = getDB();
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ComedianDetailPageData } from "../../../(entities)/(detail)/comedian/[name]/interface";

export async function GET(request: Request, { params }) {
    const slug = await params

    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await database.queries.getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug);

    return database.page.getComedianDetailPageData(helper.asQueryFilters())
        .then((data: ComedianDetailPageData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
