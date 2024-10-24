import { auth } from "@/auth";
import { PUBLIC_ROUTES } from "@/lib/routes";
import { NextResponse } from "next/server";

export async function POST(
    request: Request
) {
    const data = await request.json();
    const url = process.env.URL_DOMAIN + PUBLIC_ROUTES.UPDATE_SOCIAL_DATA
    const session = await auth();

    const response = await fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams(data),
    })
        .then((response) => response.json())
        .catch((error) => console.error(error))

    return NextResponse.json(response)
}