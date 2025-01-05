
import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { EntityType } from "../../../../objects/enum";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { ClubDetailPageData } from "../../../(entities)/(detail)/club/[name]/interface";
import { headers } from "next/headers";
const { database } = getDB();

export async function GET(request: Request, { params }) {
    const headersList = await headers();
    const userId = headersList.get("user_id");

    const slug = await params
    const newURL = new URL(request.url);
    const searchParams = newURL.searchParams
    const filters = await database.queries.getTags(EntityType.Comedian);

    const helper = await QueryHelper.storePageParams(searchParams, filters, slug, userId);

    return database.page.getClubDetailPageData(helper.asQueryFilters())
        .then((data: ClubDetailPageData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
