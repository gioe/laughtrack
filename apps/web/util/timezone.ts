import { NextRequest } from "next/server";

const HEADER_NAME = "X-Timezone";
const COOKIE_NAME = "timezone";
const DEFAULT_TIMEZONE = "UTC";

/**
 * Returns true iff `tz` is a valid IANA timezone identifier accepted by ICU.
 *
 * Intl.DateTimeFormat's constructor throws RangeError on unknown zones; a clean
 * construction is the same validity check ICU itself uses, so it tracks the
 * tz database without us shipping a hardcoded list.
 */
export function isValidTimezone(tz: string): boolean {
    try {
        new Intl.DateTimeFormat(undefined, { timeZone: tz });
        return true;
    } catch {
        return false;
    }
}

export type ReadTimezoneResult =
    | { ok: true; timezone: string }
    | { ok: false; error: string };

/**
 * Resolves the X-Timezone header to a validated IANA zone, or signals an
 * invalid value so the caller can return 400.
 *
 * Routes pre-TASK-1829 passed the raw header straight into date-fns-tz; an
 * invalid value (e.g. 'Not/Real') made tzParseTimezone return NaN, producing
 * Invalid Date for Prisma's gte/lte bounds. Prisma rejected the query and the
 * route silently degraded to []. Validating up front and returning 400 lets
 * clients (notably iOS) surface the malformed header instead of seeing an
 * empty list.
 */
export function readTimezoneHeader(req: NextRequest): ReadTimezoneResult {
    const raw = req.headers.get(HEADER_NAME);
    if (raw === null) return { ok: true, timezone: DEFAULT_TIMEZONE };
    if (!isValidTimezone(raw)) {
        // Pre-TASK-1829 a malformed value silently fell through to an empty list,
        // so a sudden spike of 400s on these routes would read as a mystery
        // regression. Log so an operator can attribute it to the offending client.
        console.warn(
            `[timezone] Rejecting invalid ${HEADER_NAME} header: ${JSON.stringify(raw)}`,
        );
        return {
            ok: false,
            error: `${HEADER_NAME} must be a valid IANA timezone identifier (e.g. America/New_York)`,
        };
    }
    return { ok: true, timezone: raw };
}

/**
 * Resolves a 'timezone' cookie value to a validated IANA zone, falling back
 * to UTC on missing or invalid input.
 *
 * SSR pages don't have an iOS caller, so an invalid cookie shouldn't 400 — it
 * should keep the page alive on a sane default. Pre-TASK-1834 the call sites
 * passed cookieStore.get('timezone')?.value straight into date-fns-tz; an
 * invalid value (e.g. 'Not/Real', a manually-edited or corrupted cookie) made
 * tzParseTimezone return NaN, producing Invalid Date for Prisma's gte/lte
 * bounds and silently degrading the route to an empty result.
 */
export function readTimezoneCookie(rawValue: string | undefined): string {
    if (rawValue === undefined || rawValue === "") return DEFAULT_TIMEZONE;
    if (!isValidTimezone(rawValue)) {
        console.warn(
            `[timezone] Rejecting invalid ${COOKIE_NAME} cookie: ${JSON.stringify(rawValue)}; falling back to ${DEFAULT_TIMEZONE}`,
        );
        return DEFAULT_TIMEZONE;
    }
    return rawValue;
}
