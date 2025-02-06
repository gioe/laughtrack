import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { HomePageDataResponse } from "./interface";
import { getHomePageData } from "@/lib/data/home/getHomePageData";

export async function GET() {
    const headersList = await headers();
    const userId = headersList.get("user_id")
    const normalizedUserId = (!userId || userId === "undefined") ? undefined : userId;
    return getHomePageData(normalizedUserId)
        .then((response: HomePageDataResponse) => NextResponse.json({ comedians: response.comedians, clubs: response.clubs }, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
