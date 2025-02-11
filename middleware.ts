
// middleware.js
import { NextRequest, NextResponse } from "next/server";
import { QueryProperty, SortParamValue } from "./objects/enum";
export { auth as middleware } from "@/auth"
import { use } from "react";
import { UserInterface } from "./objects/class/user/user.interface";

// export async function middleware(request: NextRequest) {
//     const session = await auth()
//     console.log(session?.user)
//     const url = new URL(request.nextUrl.pathname, request.url);
//     const searchParams = new URLSearchParams(request.nextUrl.search);

//     setParamDefaults(searchParams, request.nextUrl.pathname, session?.user)

//     for (const [key, value] of searchParams.entries()) {
//         url.searchParams.set(key, value);
//     }
//     return NextResponse.rewrite(url)
// }

export function setParamDefaults(params: URLSearchParams, path: string, user?: UserInterface): URLSearchParams {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    if (!params.has(QueryProperty.Sort)) { getSortParamDefaultFromPath(params, path) }
    if (!params.has(QueryProperty.Page)) { params.set(QueryProperty.Page, "1") }
    if (!params.has(QueryProperty.Size)) { params.set(QueryProperty.Size, "10") }
    if (!params.has(QueryProperty.Direction)) { params.set(QueryProperty.Direction, "asc") }
    if (!params.has(QueryProperty.Zip)) { params.set(QueryProperty.Zip, user?.zipCode ?? "10003")}
    if (!params.has(QueryProperty.FromDate)) { params.set(QueryProperty.FromDate, today.toISOString())}
    if (!params.has(QueryProperty.ToDate)) { params.set(QueryProperty.ToDate, tomorrow.toISOString())}

    return params
}

function getSortParamDefaultFromPath(params: URLSearchParams, path: string): URLSearchParams {
    if (path.startsWith('/club') || path.startsWith('/comedian')) {
        params.set(QueryProperty.Sort, path.includes('/all') ? SortParamValue.Name : SortParamValue.Date)
    } else if (path.startsWith('/show')) {
        params.set(QueryProperty.Sort, path.includes('/all') ? SortParamValue.Date : SortParamValue.Name)
    }
    return params
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
