
// middleware.js
import { NextRequest, NextResponse } from "next/server";
import { QueryProperty, SortParamValue } from "./objects/enum";
import { auth } from "./auth";
import { formattedDateParam } from "./util/primatives/paramUtil";
import { UserInterface } from "./objects/class/user/user.interface";
import { Session } from "next-auth";

const protectedRoutes = [
    '/profile',
  ]

function isProtectedRoute(pathname: string): boolean {
    return protectedRoutes.some(route => pathname.startsWith(route))
}
export async function middleware(request: NextRequest) {
    const pathname = request.nextUrl.pathname
    const session = await auth()

    if (!isProtectedRoute(pathname)) {
        return handlePublicRoute(request, session)
    }

    if (!session) {
        const loginUrl = new URL('/', request.url)
        loginUrl.searchParams.set('callbackUrl', pathname)
        return NextResponse.redirect(loginUrl)
    }

    // Special handling for profile route
    if (pathname.startsWith('/profile')) {
        const userId = session.user?.id
        if (!userId) {
            return NextResponse.redirect(new URL('/', request.url))
        }

        // Internal rewrite to your API endpoint
        return NextResponse.rewrite(new URL(`/profile/${userId}`, request.url))
    }

    return NextResponse.next()
}

async function handlePublicRoute(request: NextRequest, session: Session | null) {
    const url = new URL(request.nextUrl.pathname, request.url);
    const searchParams = new URLSearchParams(request.nextUrl.search);

    setParamDefaults(searchParams, request.nextUrl.pathname, session?.user)

    for (const [key, value] of searchParams.entries()) {
        url.searchParams.set(key, value);
    }

    return NextResponse.rewrite(url)
}


export function setParamDefaults(params: URLSearchParams, path: string, user?: UserInterface): URLSearchParams {

    if (!params.has(QueryProperty.Sort)) { getSortParamDefaultFromPath(params, path) }
    if (!params.has(QueryProperty.Page)) { params.set(QueryProperty.Page, "1") }
    if (!params.has(QueryProperty.Size)) { params.set(QueryProperty.Size, "10") }
    if (!params.has(QueryProperty.Direction)) { params.set(QueryProperty.Direction, "asc") }
    if (!params.has(QueryProperty.Zip)) { params.set(QueryProperty.Zip, user?.zipCode ?? "10003")}
    if (!params.has(QueryProperty.FromDate)) { params.set(QueryProperty.FromDate, formattedDateParam(new Date()))}
    if (!params.has(QueryProperty.Distance)) { params.set(QueryProperty.Distance, "5")}

    return params
}

function getSortParamDefaultFromPath(params: URLSearchParams, path: string): URLSearchParams {
    if (path.startsWith('/club') || path.startsWith('/comedian')) {
        params.set(QueryProperty.Sort, path.includes('/search') ? SortParamValue.Name : SortParamValue.Date)
    } else if (path.startsWith('/show')) {
        params.set(QueryProperty.Sort, path.includes('/search') ? SortParamValue.Date : SortParamValue.Name)
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
