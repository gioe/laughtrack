

import { NextResponse } from "next/server";
import { getDB } from '../../../../../database'
import { EditComedianPageDTO } from "../../../../(entities)/(detail)/comedian/[name]/admin/interface";
const { database } = getDB();

export async function GET(request: Request, { params }) {
    const slug = await params

    return database.page.getEditClubDetailPageData(slug)
        .then((data: EditComedianPageDTO) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
