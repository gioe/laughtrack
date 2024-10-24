import { PUBLIC_ROUTES } from "@/lib/routes";
import { NextResponse } from "next/server";

export async function GET() {
    const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_TRENDING_COMEDIANS

    const response = await fetch(url, {
        cache: 'no-store',
        method: "POST",
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
        .then((response) => response.json())
        .catch((error) => console.error(error))

    return NextResponse.json(response)
}
