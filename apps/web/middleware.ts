// middleware.js
import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { QueryProperty, SortParamValue } from "./objects/enum";
import { UserInterface } from "./objects/class/user/user.interface";
import { getCorsHeaders } from "./lib/cors";

const SECURITY_HEADERS: Record<string, string> = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https://laughtrack.b-cdn.net https://lh3.googleusercontent.com",
        "font-src 'self' data:",
        "connect-src 'self' https:",
        "frame-ancestors 'none'",
    ].join("; "),
    "Permissions-Policy":
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
};

function applySecurityHeaders(response: NextResponse): NextResponse {
    for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
        response.headers.set(key, value);
    }
    return response;
}

// Patterns for routes that require authentication.
// Add new protected route prefixes here as the app grows.
const PROTECTED_ROUTE_PATTERNS: RegExp[] = [/^\/profile(\/|$)/];

function isProtectedRoute(pathname: string): boolean {
    return PROTECTED_ROUTE_PATTERNS.some((pattern) => pattern.test(pathname));
}

export async function middleware(request: NextRequest) {
    try {
        const pathname = request.nextUrl.pathname;

        // Handle CORS for all API routes and return early — API routes manage their own auth
        if (pathname.startsWith("/api")) {
            const origin = request.headers.get("origin");
            const corsHeaders = getCorsHeaders(origin);

            if (request.method === "OPTIONS") {
                const preflightResponse = new NextResponse(null, {
                    status: 200,
                    headers: corsHeaders,
                });
                return applySecurityHeaders(preflightResponse);
            }

            const response = NextResponse.next();
            Object.entries(corsHeaders).forEach(([key, value]) => {
                response.headers.set(key, value);
            });
            return applySecurityHeaders(response);
        }

        const url = request.nextUrl.clone();
        const searchParams = new URLSearchParams(url.search);

        // Apply default parameters
        setParamDefaults(searchParams, pathname);

        // Update the URL with the modified search params
        url.search = searchParams.toString();
        const response = NextResponse.rewrite(url);

        // Handle protected routes
        if (!isProtectedRoute(pathname)) {
            return applySecurityHeaders(response);
        }

        const token = await getToken({ req: request });

        if (!token) {
            const loginUrl = new URL("/", request.url);
            loginUrl.searchParams.set("callbackUrl", pathname);
            return applySecurityHeaders(NextResponse.redirect(loginUrl));
        }

        // Special handling for profile route
        if (pathname.startsWith("/profile")) {
            const userId = token.sub;
            if (!userId) {
                return applySecurityHeaders(
                    NextResponse.redirect(new URL("/", request.url)),
                );
            }

            const requestedProfileId = pathname.split("/").pop();

            if (requestedProfileId && userId !== requestedProfileId) {
                // User is trying to access another user's profile - redirect to their own profile
                return applySecurityHeaders(
                    NextResponse.redirect(
                        new URL(`/profile/${userId}`, request.url),
                    ),
                );
            }
        }

        return applySecurityHeaders(response);
    } catch (error) {
        console.error("Middleware error:", error);
        return applySecurityHeaders(NextResponse.next());
    }
}

export function setParamDefaults(
    params: URLSearchParams,
    path: string,
    user?: UserInterface,
): URLSearchParams {
    if (!params.has(QueryProperty.Sort)) {
        getSortParamDefaultFromPath(params, path);
    }
    if (!params.has(QueryProperty.Page)) {
        params.set(QueryProperty.Page, "1");
    }
    if (!params.has(QueryProperty.Size)) {
        params.set(QueryProperty.Size, "10");
    }
    if (!params.has(QueryProperty.Direction)) {
        params.set(QueryProperty.Direction, "asc");
    }
    if (!params.has(QueryProperty.Zip)) {
        params.set(QueryProperty.Zip, user?.zipCode ?? "");
    }
    // Intentionally do not default fromDate. Injecting the server's UTC "today"
    // into the URL caused React hydration error #418: CalendarDisplay renders
    // date-fns isToday/isTomorrow labels in local time, so a server render in
    // UTC and a client render in a non-UTC tz produce different text for the
    // same URL param. Callers (findShowsWithCount, findComediansWithCount)
    // apply their own upcoming-only default when no date params are present.
    if (!params.has(QueryProperty.Distance)) {
        params.set(QueryProperty.Distance, "5");
    }

    return params;
}

function getSortParamDefaultFromPath(
    params: URLSearchParams,
    path: string,
): URLSearchParams {
    if (path.startsWith("/club")) {
        // /club/search defaults to "Most Active" (totalShows desc) so the
        // busiest clubs surface first — popularity is effectively unpopulated
        // for clubs, and alphabetical ordering buries active venues.
        params.set(
            QueryProperty.Sort,
            path.includes("/search")
                ? SortParamValue.TotalShowsDesc
                : SortParamValue.DateAsc,
        );
    } else if (path.startsWith("/comedian")) {
        // /comedian/search defaults to "Most Popular" (popularity desc) to
        // match the UI's sortOptions[0] — comedians have populated popularity
        // data, and alphabetical ordering buries well-known comedians.
        params.set(
            QueryProperty.Sort,
            path.includes("/search")
                ? SortParamValue.PopularityDesc
                : SortParamValue.DateAsc,
        );
    } else if (path.startsWith("/show")) {
        params.set(QueryProperty.Sort, SortParamValue.DateAsc);
    }
    return params;
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
        "/((?!static|favicon.ico|_next|images).*)",
    ],
};
