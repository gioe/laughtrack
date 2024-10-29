import { NextResponse } from "next/server";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { generateUrl } from "../../../util/urlUtil";


export async function POST(
    request: Request
) {
    const data = await request.json();

    const url = generateUrl(PUBLIC_ROUTES.REGISTER);

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
            email: data.email,
            password: data.password,
        }),
    })
        .then((response) => response.json())
        .catch((error) => console.error(error))

    return NextResponse.json(response)
}

