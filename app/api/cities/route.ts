import { NextResponse } from "next/server";
import { getDB } from '../../../database'
import { CityDTO } from "../../../objects/class/city/city.interface";
const { database } = getDB();

export async function GET() {
    return database.queries.getCities()
        .then((cities: CityDTO[]) => {
            console.log(cities)
            return NextResponse.json({ cities }, { status: 200 })
        })
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
