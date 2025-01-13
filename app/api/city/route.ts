import { NextResponse } from "next/server";
import { getCities } from "@/lib/data/cities/get";
import { CityDTO } from "@/objects/class/city/city.interface";

export async function GET() {
    return getCities()
        .then((cities: CityDTO[]) => NextResponse.json({ cities }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
