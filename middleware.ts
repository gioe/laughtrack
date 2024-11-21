export { auth } from "./auth";


// middleware.js

import { NextRequest, NextResponse } from "next/server";
import { DirectionParamValue, SortParamValue } from "./objects/enum";

export function middleware(request: NextRequest) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-pathname", request.nextUrl.pathname);

    const newUrl = createNewUrl(request)

    if (request.nextUrl.pathname.startsWith('/club')) {
        if (request.nextUrl.pathname.includes('/all')) {
            newUrl.searchParams.set('sort_by', SortParamValue.Name)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        } else {
            newUrl.searchParams.set('sort_by', SortParamValue.Date)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        }
    } else if (request.nextUrl.pathname.startsWith('/show')) {
        if (request.nextUrl.pathname.includes('/all')) {
            newUrl.searchParams.set('sort_by', SortParamValue.Name)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        } else {
            newUrl.searchParams.set('sort_by', SortParamValue.Name)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        }
    } else if (request.nextUrl.pathname.startsWith('/comedian')) {
        if (request.nextUrl.pathname.includes('/all')) {
            newUrl.searchParams.set('sort_by', SortParamValue.Name)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        } else {
            newUrl.searchParams.set('sort_by', SortParamValue.Date)
            newUrl.searchParams.set('direction', DirectionParamValue.Ascending)
        }
    }

    console.log(`Returned params: ${newUrl.searchParams}`)
    return NextResponse.rewrite(newUrl)
}

const createNewUrl = (request: NextRequest): URL => {
    const url = new URL(request.nextUrl.pathname, request.url);
    const splitSearch = request.nextUrl.search.split('?')
    if (splitSearch.length > 1) {
        const params = splitSearch[1].split("&")
        const dict = new Map<string, string>();
        params.forEach((param: string) => {
            const splitParam = param.split("=")
            dict.set(splitParam[0], splitParam[1])
        })
        for (const [key, value] of dict) {
            url.searchParams.set(key, value);
        }
    }
    return url
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
