import { NextResponse } from "next/server";
import { getDB } from '../../../../database'
import { ComedianDTO } from "../../../../objects/class/comedian/comedian.interface";
const { database } = getDB();

export async function GET() {
    return database.queries.getTrendingComedians()
        .then((entities: ComedianDTO[]) => NextResponse.json({ entities }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
