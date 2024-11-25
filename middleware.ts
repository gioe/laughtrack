export { auth } from "./auth";

// middleware.js

import { NextRequest, NextResponse } from "next/server";
import { setParamDefaults } from "./util/primatives/paramUtil";

export function middleware(request: NextRequest) {

    const url = new URL(request.nextUrl.pathname, request.url);
    const searchParams = new URLSearchParams(request.nextUrl.search);

    setParamDefaults(searchParams, request.nextUrl.pathname)

    for (const [key, value] of searchParams.entries()) {
        console.log(`The key is ${key} and the value is ${value}`)
        url.searchParams.set(key, value);
    }

    return NextResponse.rewrite(url)
}



export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - static (static files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|static|favicon.ico|_next|images).*)',
    ],
}
