import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../../database";
const { database } = getDB();

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const slug = await params

    return database.actions.deleteShowsForClub(slug)
        .then(() => {
            return NextResponse.json({ success: true }, { status: 200 })
        })
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error }, { status: 500 })
        })

}
