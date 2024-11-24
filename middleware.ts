export { auth } from "./auth";

// middleware.js

import { NextRequest, NextResponse } from "next/server";
import { SortParamValue } from "./objects/enum";
import { QueryProperty } from "./objects/enum/queryProperty";

export function middleware(request: NextRequest) {

    const url = new URL(request.nextUrl.pathname, request.url);
    const searchParams = new URLSearchParams(request.nextUrl.search);

    if (request.nextUrl.pathname.startsWith('/club')) {
        if (request.nextUrl.pathname.includes('/all')) {
            searchParams.set(QueryProperty.Sort, SortParamValue.Name)
        } else {
            searchParams.set(QueryProperty.Sort, SortParamValue.Date)
        }
    } else if (request.nextUrl.pathname.startsWith('/show')) {
        if (request.nextUrl.pathname.includes('/all')) {
            searchParams.set(QueryProperty.Sort, SortParamValue.Date)
        } else {
            searchParams.set(QueryProperty.Sort, SortParamValue.Name)
        }
    } else if (request.nextUrl.pathname.startsWith('/comedian')) {
        if (request.nextUrl.pathname.includes('/all')) {
            searchParams.set(QueryProperty.Sort, SortParamValue.Name)
        } else {
            searchParams.set(QueryProperty.Sort, SortParamValue.Date)
        }
    }

    for (const [key, value] of searchParams.entries()) {
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
