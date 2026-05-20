// middleware.js
import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { QueryProperty, SortParamValue } from "./objects/enum";
import { UserInterface } from "./objects/class/user/user.interface";
import { getCorsHeaders } from "./lib/cors";

const IS_DEV = process.env.NODE_ENV === "development";

// React Refresh evaluates compiled strings as JS during dev hydration, which
// requires 'unsafe-eval'. Prod must never include it.
// https://va.vercel-scripts.com hosts the Vercel Analytics script (script.js
// in prod, script.debug.js in dev).
const SCRIPT_SRC = IS_DEV
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://va.vercel-scripts.com"
    : "script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com";

// connect-src allow-list:
// - 'self' covers same-origin API routes plus Vercel Analytics / Speed Insights
//   beacons (posted to /_vercel/insights/* and /_vercel/speed-insights/*).
// - https://va.vercel-scripts.com is a defensive entry for any fetch initiated
//   by the Vercel Analytics script back to its host.
// - https://*.ingest.sentry.io plus regional variants cover the @sentry/nextjs
//   browser SDK's error/trace ingest (host depends on the DSN's region).
const CONNECT_SRC = [
    "connect-src",
    "'self'",
    "https://va.vercel-scripts.com",
    "https://*.ingest.sentry.io",
    "https://*.ingest.us.sentry.io",
    "https://*.ingest.de.sentry.io",
].join(" ");

const SECURITY_HEADERS: Record<string, string> = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": [
        "default-src 'self'",
        SCRIPT_SRC,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https://laughtrack.b-cdn.net https://lh3.googleusercontent.com",
        "font-src 'self' data:",
        CONNECT_SRC,
        "frame-ancestors 'none'",
    ].join("; "),
    "Permissions-Policy":
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
};

const CANONICAL_HOSTS = new Set([
    "laugh-track.com",
    "www.laugh-track.com",
    "localhost",
    "127.0.0.1",
]);

function getRequestHost(request: NextRequest): string {
    return (request.headers.get("host") ?? request.nextUrl.host)
        .split(":")[0]
        .toLowerCase();
}

function applySecurityHeaders(
    response: NextResponse,
    request: NextRequest,
): NextResponse {
    for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
        response.headers.set(key, value);
    }
    if (!CANONICAL_HOSTS.has(getRequestHost(request))) {
        response.headers.set("X-Robots-Tag", "noindex");
    }
    return response;
}

// Patterns for routes that require authentication.
// Add new protected route prefixes here as the app grows.
const PROTECTED_ROUTE_PATTERNS: RegExp[] = [/^\/profile(\/|$)/];
const DEFAULT_PAGE_SIZE = "20";
const COMEDIAN_DETAIL_PAGE_SIZE = "5";

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
                return applySecurityHeaders(preflightResponse, request);
            }

            const response = NextResponse.next();
            Object.entries(corsHeaders).forEach(([key, value]) => {
                response.headers.set(key, value);
            });
            return applySecurityHeaders(response, request);
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
            return applySecurityHeaders(response, request);
        }

        const token = await getToken({ req: request });

        if (!token) {
            const loginUrl = new URL("/", request.url);
            loginUrl.searchParams.set("callbackUrl", pathname);
            return applySecurityHeaders(
                NextResponse.redirect(loginUrl),
                request,
            );
        }

        // Special handling for profile route
        if (pathname.startsWith("/profile")) {
            const userId = token.sub;
            if (!userId) {
                return applySecurityHeaders(
                    NextResponse.redirect(new URL("/", request.url)),
                    request,
                );
            }

            const requestedProfileId = pathname.split("/").pop();

            if (requestedProfileId && userId !== requestedProfileId) {
                // User is trying to access another user's profile - redirect to their own profile
                return applySecurityHeaders(
                    NextResponse.redirect(
                        new URL(`/profile/${userId}`, request.url),
                    ),
                    request,
                );
            }
        }

        return applySecurityHeaders(response, request);
    } catch (error) {
        console.error("Middleware error:", error);
        return applySecurityHeaders(NextResponse.next(), request);
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
        params.set(QueryProperty.Size, getSizeParamDefaultFromPath(path));
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

function getSizeParamDefaultFromPath(path: string): string {
    if (path.startsWith("/comedian/") && !path.startsWith("/comedian/search")) {
        return COMEDIAN_DETAIL_PAGE_SIZE;
    }
    return DEFAULT_PAGE_SIZE;
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
    } else if (path.startsWith("/podcast")) {
        // /podcast/search defaults to "Most Episodes" (show count desc) so
        // active podcasts surface first — mirrors iOS PodcastSortOption.mostEpisodes.
        params.set(QueryProperty.Sort, SortParamValue.ShowCountDesc);
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
