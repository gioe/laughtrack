import { waitUntil } from "@vercel/functions";
import type { NextRequest } from "next/server";
import { normalizeRoutePattern, recordRequestMetric } from "./requestMetrics";

// Vercel publishes the active serverless request context on globalThis under
// this well-known symbol (the same one @vercel/functions' internal getContext()
// reads). Its presence — and a callable waitUntil on the resolved store — is how
// we tell a real request apart from local dev / unit tests, where there is no
// context. Note that waitUntil() does NOT throw off-context: getContext() simply
// returns {} and the optional `waitUntil?.()` call no-ops. So we must detect the
// context ourselves rather than relying on waitUntil to reject.
const REQUEST_CONTEXT_SYMBOL = Symbol.for("@vercel/request-context");

type RequestContextStore = {
    get?: () => { waitUntil?: unknown } | undefined;
};

function hasServerlessRequestContext(): boolean {
    const store = (globalThis as Record<symbol, unknown>)[
        REQUEST_CONTEXT_SYMBOL
    ] as RequestContextStore | undefined;
    return typeof store?.get?.()?.waitUntil === "function";
}

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

function scheduleMetricWrite(makeWritePromise: () => Promise<unknown>): void {
    try {
        // Only start the detached write inside an actual serverless request
        // context. Bail BEFORE building the write promise — otherwise the write
        // fires against an unconfigured Prisma client and logs a benign-but-noisy
        // connection failure ("No database host…" / "$executeRaw is not a
        // function") to stderr on every request the unit-test suite exercises.
        if (!hasServerlessRequestContext()) {
            return;
        }
        // Inside a request context: register the real write through waitUntil so
        // it settles off the response critical path without blocking the response.
        waitUntil(makeWritePromise());
    } catch {
        // Metrics scheduling is best-effort and must never throw out of the
        // handler path (this runs in the wrapper's finally block). Swallow any
        // context-detection or registration error rather than masking the
        // response — or the handler's own error — being returned.
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
            // Pass a factory rather than a live promise so the DB write is only
            // started once scheduleMetricWrite confirms an active request context
            // (see its waitUntil probe). Building the promise eagerly here would
            // fire the write even when there is no context to run it in.
            scheduleMetricWrite(() =>
                (async () => {
                    const routePattern = await resolveRoutePattern(req, ctx);
                    await recordRequestMetric({ routePattern, method, status });
                })().catch((error) => {
                    // Metrics are best-effort: a recording failure must never
                    // break the request it was observing.
                    console.error(
                        "[withRequestMetrics] failed to record request metric",
                        error,
                    );
                }),
            );
        }
    };

    return wrapped as H;
}
