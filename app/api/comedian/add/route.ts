import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { generateHash } from "../../../../util/hashUtil";
const { database } = getDB();

export async function POST(
    req: NextRequest,
) {
    const { name } = await req.json()
    console.log(name)
    return database.actions.addComedian({
        name,
        uuid: generateHash(name)
    })
        .then(() => NextResponse.json({}, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            NextResponse.json({ message: error.message }, { status: 500 })
        });
}
