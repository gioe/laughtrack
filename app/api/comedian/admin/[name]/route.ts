/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'
const { database } = getDB();
import { EditComedianPageData } from "../../../../(entities)/(detail)/comedian/admin/[name]/interface";

export async function GET(request: Request, { params }) {
    const slug = await params

    return database.page.getEditComedianDetailPageData(slug)
        .then((data: EditComedianPageData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}

export async function PUT(request: NextRequest, { params }) {
    const slug = await params
    const body = await request.json()

    return database.actions.updateComedian(slug, body)
        .then((data: any) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
