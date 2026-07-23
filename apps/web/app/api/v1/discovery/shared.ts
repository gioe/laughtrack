import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import {
    RATE_LIMITS,
    checkRateLimit,
    getClientIp,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";

export const MAX_DISCOVERY_BATCH_SIZE = 50;
export const ANONYMOUS_VISITOR_COOKIE = "lt_anon_visitor_id";

const ANONYMOUS_VISITOR_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 395;
const UUID_PATTERN =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const POLICY_VERSION_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/i;
const MAX_EVENT_AGE_MS = 24 * 60 * 60 * 1000;
const MAX_EVENT_FUTURE_MS = 5 * 60 * 1000;

export type DiscoveryActor = {
    profileId: string | null;
    anonymousVisitorId: string;
    shouldSetAnonymousCookie: boolean;
};

export function isUuid(value: unknown): value is string {
    return typeof value === "string" && UUID_PATTERN.test(value);
}

export function isPolicyVersion(value: unknown): value is string {
    return typeof value === "string" && POLICY_VERSION_PATTERN.test(value);
}

export function parseEventTime(value: unknown, now = Date.now()): Date | null {
    if (typeof value !== "string") return null;
    const parsed = new Date(value);
    const timestamp = parsed.getTime();
    if (
        Number.isNaN(timestamp) ||
        timestamp < now - MAX_EVENT_AGE_MS ||
        timestamp > now + MAX_EVENT_FUTURE_MS
    ) {
        return null;
    }
    return parsed;
}

export function parseBatch(payload: unknown): unknown[] | null {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
        return null;
    }
    const events = (payload as Record<string, unknown>).events;
    if (
        !Array.isArray(events) ||
        events.length < 1 ||
        events.length > MAX_DISCOVERY_BATCH_SIZE
    ) {
        return null;
    }
    return events;
}

export async function resolveDiscoveryActor(
    req: NextRequest,
): Promise<DiscoveryActor> {
    const authContext = await resolveAuth(req);
    const profileId =
        authContext && authContext !== PROFILE_MISSING
            ? authContext.profileId
            : null;
    const existingAnonymousId = req.cookies.get(
        ANONYMOUS_VISITOR_COOKIE,
    )?.value;

    return {
        profileId,
        anonymousVisitorId:
            existingAnonymousId && existingAnonymousId.length <= 128
                ? existingAnonymousId
                : randomUUID(),
        shouldSetAnonymousCookie: !(
            existingAnonymousId && existingAnonymousId.length <= 128
        ),
    };
}

export async function applyDiscoveryWriteRateLimit(
    req: NextRequest,
    actor: DiscoveryActor,
    routePrefix: string,
) {
    const key = actor.profileId
        ? `${routePrefix}:profile:${actor.profileId}`
        : `${routePrefix}:anon-ip:${getClientIp(req)}`;
    const config = actor.profileId
        ? RATE_LIMITS.authenticated
        : RATE_LIMITS.unauthenticated;
    const result = await checkRateLimit(key, config);
    return result.allowed ? result : rateLimitResponse(result);
}

export function setAnonymousVisitorCookie(
    response: NextResponse,
    actor: DiscoveryActor,
): void {
    if (!actor.shouldSetAnonymousCookie) return;
    response.cookies.set(ANONYMOUS_VISITOR_COOKIE, actor.anonymousVisitorId, {
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: ANONYMOUS_VISITOR_COOKIE_MAX_AGE_SECONDS,
    });
}
