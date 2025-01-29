import { NextResponse } from "next/server";
import { getSearchedComedians } from "@/lib/data/comedian/getSearchedComedians";
import { ComedianSearchResponse } from "./interface";
import { headers } from "next/headers";

export async function GET(request: Request) {

    const headersList = await headers();
    const searchParams = new URL(request.url).searchParams

    return getSearchedComedians(searchParams, headersList)
        .then((response: ComedianSearchResponse) => NextResponse.json({
            data: response.data,
            total: response.total,
            filters: response.filters
        }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
