/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { HomePageDTO } from "./interface";
import { getHomePageData } from "@/lib/data/home/get";

export async function GET(request: Request) {
    const headersList = await headers();
    const userId = headersList.get("user_id");

    return getHomePageData(userId)
        .then((response: HomePageDTO) => NextResponse.json({ response }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
