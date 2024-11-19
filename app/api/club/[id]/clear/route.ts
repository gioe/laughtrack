import { NextRequest, NextResponse } from "next/server";
import { apiActionMap } from "../../../../../database/sql";
import { getDB } from "../../../../../database";
const { database } = getDB();

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const slug = await params
    const file = apiActionMap.club.slug.delete.show;

    return database.any(file, slug)
        .then(() => {
            return NextResponse.json({ success: true }, { status: 200 })
        })
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error }, { status: 500 })

        })

}
