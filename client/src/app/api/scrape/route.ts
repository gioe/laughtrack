import { PUBLIC_ROUTES } from "@/lib/routes";
import { NextResponse } from "next/server";

export async function POST(
    request: Request
) {
    const data = await request.json();
    const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.SCRAPE

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(data)
    })
        .then((response) => response.json())
        .catch((error) => console.error(error))

    return NextResponse.json(response)
}

