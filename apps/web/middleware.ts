// middleware.js
import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { QueryProperty, SortParamValue } from "./objects/enum";
import { formattedDateParam } from "./util/primatives/paramUtil";
import { UserInterface } from "./objects/class/user/user.interface";
import { getCorsHeaders } from "./lib/cors";

const protectedRoutes = [
    '/profile',
]

function isProtectedRoute(pathname: string): boolean {
    return protectedRoutes.some(route => pathname.startsWith(route))
}

export async function middleware(request: NextRequest) {
    try {
        const pathname = request.nextUrl.pathname

        // Handle CORS for all API routes and return early — API routes manage their own auth
        if (pathname.startsWith('/api')) {
            const origin = request.headers.get('origin')
            const corsHeaders = getCorsHeaders(origin)

            if (request.method === 'OPTIONS') {
                return new NextResponse(null, { status: 200, headers: corsHeaders })
            }

            const response = NextResponse.next()
            Object.entries(corsHeaders).forEach(([key, value]) => {
                response.headers.set(key, value)
            })
            return response
        }

        const url = request.nextUrl.clone()
        const searchParams = new URLSearchParams(url.search)

        // Apply default parameters
        setParamDefaults(searchParams, pathname)

        // Update the URL with the modified search params
        url.search = searchParams.toString()
        const response = NextResponse.rewrite(url)

        // Handle protected routes
        if (!isProtectedRoute(pathname)) {
            return response
        }

        const token = await getToken({ req: request })

        if (!token) {
            const loginUrl = new URL('/', request.url)
            loginUrl.searchParams.set('callbackUrl', pathname)
            return NextResponse.redirect(loginUrl)
        }

        // Special handling for profile route
        if (pathname.startsWith('/profile')) {
            const userId = token.sub
            if (!userId) {
                return NextResponse.redirect(new URL('/', request.url))
            }

            const requestedProfileId = pathname.split('/').pop()

            if (requestedProfileId && userId !== requestedProfileId) {
                // User is trying to access another user's profile - redirect to their own profile
                return NextResponse.redirect(new URL(`/profile/${userId}`, request.url))
            }
        }

        return response
    } catch (error) {
        console.error('Middleware error:', error)
        return NextResponse.next()
    }
}

export function setParamDefaults(params: URLSearchParams, path: string, user?: UserInterface): URLSearchParams {

    if (!params.has(QueryProperty.Sort)) { getSortParamDefaultFromPath(params, path) }
    if (!params.has(QueryProperty.Page)) { params.set(QueryProperty.Page, "1") }
    if (!params.has(QueryProperty.Size)) { params.set(QueryProperty.Size, "10") }
    if (!params.has(QueryProperty.Direction)) { params.set(QueryProperty.Direction, "asc") }
    if (!params.has(QueryProperty.Zip)) { params.set(QueryProperty.Zip, user?.zipCode ?? "")}
    if (!params.has(QueryProperty.FromDate)) { params.set(QueryProperty.FromDate, formattedDateParam(new Date()))}
    if (!params.has(QueryProperty.Distance)) { params.set(QueryProperty.Distance, "5")}

    return params
}

function getSortParamDefaultFromPath(params: URLSearchParams, path: string): URLSearchParams {
    if (path.startsWith('/club') || path.startsWith('/comedian')) {
        params.set(QueryProperty.Sort, path.includes('/search') ? SortParamValue.NameAsc : SortParamValue.DateAsc)
    } else if (path.startsWith('/show')) {
        params.set(QueryProperty.Sort,  SortParamValue.DateAsc)
    }
    return params
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - static (static files)
         * - favicon.ico (favicon file)
         * - _next (Next.js internals)
         * - images (static image files)
         */
        '/((?!static|favicon.ico|_next|images).*)',
    ],
}
