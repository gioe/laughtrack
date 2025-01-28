import { NextResponse } from "next/server";
import { CityDTO, getCities } from "@/lib/data/cities/getCities";

export async function GET() {
    return getCities()
        .then((cities: CityDTO[]) => NextResponse.json({ cities }, { status: 200 }))
        .catch((error: Error) => {
            console.error(error.message)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
