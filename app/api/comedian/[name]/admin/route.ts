/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'
import { EditComedianPageData } from "../../../../(entities)/(detail)/comedian/[name]/admin/interface";
const { database } = getDB();

export async function GET(request: Request, { params }) {
    const slug = await params

    return database.page.getEditComedianDetailPageData(slug)
        .then((data: EditComedianPageData) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}

export async function PUT(request: NextRequest, { params }) {
    const slug = await params
    const body = await request.json()

    console.log(body)

    return database.actions.updateComedian(slug, body)
        .then((data: any) => NextResponse.json({ data }, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
