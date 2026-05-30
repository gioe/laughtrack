import { waitUntil } from "@vercel/functions";
import type { NextRequest } from "next/server";
import { normalizeRoutePattern, recordRequestMetric } from "./requestMetrics";

type RouteParams = Record<string, string | string[]>;

// Next.js 15 passes params as a Promise in the second handler argument. Static
// routes receive no second argument at all, so the whole context is optional.
type RouteContext = { params?: Promise<RouteParams> };

// Constraint for the wrapped handler. Deliberately permissive on arguments so
// it accepts both static handlers (no second arg) and dynamic-route handlers
// (a required `{ params }` context) without contravariance friction — Next.js
// route exports use a variety of exact signatures. The wrapper preserves the
// original signature (returns H) so the route export still type-checks against
// Next's generated types.
type RouteHandler = (...args: any[]) => Response | Promise<Response>;

function getPathname(req?: NextRequest): string {
    // NextRequest exposes a parsed URL; fall back to parsing req.url for plain
    // Request objects (e.g. in unit tests). Tolerate a missing req entirely —
    // metrics must never throw out of the handler path.
    if (!req) {
        return "/";
    }
    if (req.nextUrl?.pathname) {
        return req.nextUrl.pathname;
    }
    try {
        return new URL(req.url).pathname;
    } catch {
        return req.url ?? "/";
    }
}

async function resolveRoutePattern(
    req: NextRequest | undefined,
    ctx?: RouteContext,
): Promise<string> {
    const pathname = getPathname(req);
    try {
        const params = ctx?.params ? await ctx.params : undefined;
        return normalizeRoutePattern(pathname, params);
    } catch {
        // If params can't be resolved we still record against the raw pathname
        // rather than dropping the metric entirely.
        return pathname;
    }
}

function scheduleMetricWrite(writePromise: Promise<unknown>): void {
    try {
        // waitUntil keeps the serverless function alive until the write settles
        // without blocking the response. Outside a Vercel request context (local
        // dev / unit tests) it throws — the promise still runs detached, so we
        // just swallow the registration error.
        waitUntil(writePromise);
    } catch {
        /* no active request context */
    }
}

/**
 * Higher-order wrapper that records every API request as a bucketed counter in
 * `api_request_metrics`. Wrap a route handler's export:
 *
 *     export const GET = withRequestMetrics(async (req, { params }) => { ... });
 *
 * It captures the route *pattern* (dynamic segments collapsed to `[param]`),
 * the HTTP method, and the response status class, then fires the UPSERT through
 * Vercel `waitUntil()` so the write stays entirely off the response critical
 * path and adds no user-facing latency. The original handler's signature is
 * preserved so Next.js route type-checking is unaffected.
 *
 * Do NOT use this in edge middleware — it cannot reach Postgres on the edge
 * runtime.
 */
export function withRequestMetrics<H extends RouteHandler>(handler: H): H {
    const wrapped = async (
        req?: NextRequest,
        ctx?: RouteContext,
    ): Promise<Response> => {
        let status = 500;
        try {
            const response = await handler(req, ctx);
            status = response.status;
            return response;
        } finally {
            const method = req?.method ?? "GET";
            const writePromise = (async () => {
                const routePattern = await resolveRoutePattern(req, ctx);
                await recordRequestMetric({ routePattern, method, status });
            })().catch((error) => {
                // Metrics are best-effort: a recording failure must never break
                // the request it was observing.
                console.error(
                    "[withRequestMetrics] failed to record request metric",
                    error,
                );
            });
            scheduleMetricWrite(writePromise);
        }
    };

    return wrapped as H;
}
