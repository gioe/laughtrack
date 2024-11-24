export { auth } from "./auth";

// middleware.js

import { NextRequest, NextResponse } from "next/server";
import { SortParamValue } from "./objects/enum";
import { SearchParamsHelper } from "./objects/class/params/SearchParamsHelper";
import { QueryProperty } from "./objects/class/query/queryProperties";

export function middleware(request: NextRequest) {
    const searchParams = new URLSearchParams(request.nextUrl.search)
    const paramsHelper = new SearchParamsHelper(searchParams)

    // if (request.nextUrl.pathname.startsWith('/club')) {
    //     if (request.nextUrl.pathname.includes('/all')) {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Name)
    //     } else {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Date)
    //     }
    // } else if (request.nextUrl.pathname.startsWith('/show')) {
    //     if (request.nextUrl.pathname.includes('/all')) {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Date)
    //     } else {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Name)
    //     }
    // } else if (request.nextUrl.pathname.startsWith('/comedian')) {
    //     if (request.nextUrl.pathname.includes('/all')) {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Name)
    //     } else {
    //         paramsHelper.setDefaultValue(QueryProperty.Sort, SortParamValue.Date)
    //     }
    // }

    const newUrl = createNewUrl(request, paramsHelper)
    return NextResponse.rewrite(newUrl)
}

const createNewUrl = (request: NextRequest, paramsHelper: SearchParamsHelper): URL => {
    const url = new URL(request.nextUrl.pathname, request.url);
    // for (const [key, value] of paramsHelper.params) {
    //     url.searchParams.set(key, value);
    // }

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
