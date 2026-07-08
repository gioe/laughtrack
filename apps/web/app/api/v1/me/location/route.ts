import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { z } from "zod";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";

// A cleared field may arrive as explicit JSON null OR as an omitted key: the
// generated OpenAPI clients (iOS swift-openapi-generator / Android) encode a
// nil field by omitting it rather than emitting null, so `.nullish()` (accepts
// null AND undefined) plus the `?? null` coalesce below treats "absent" the
// same as "null" — clearing the saved value either way. TASK-3631.
const ProfileLocationUpdateSchema = z.object({
    zipCode: z
        .string()
        .regex(/^\d{5}$/, "zipCode must be a 5-digit US zip code")
        .nullish(),
    nearbyDistanceMiles: z.number().int().positive().nullish(),
});

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-location-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json({ error: "profile_missing" }, { status: 422 });
    }
    if (!authCtx) {
        return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }

    const rl = await checkRateLimit(
        `me-location:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    let body: unknown;
    try {
        body = await req.json();
    } catch {
        return NextResponse.json(
            { error: "Invalid JSON body" },
            { status: 400 },
        );
    }

    const parsed = ProfileLocationUpdateSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
        );
    }

    const updatedProfile = await db.userProfile.update({
        where: { userid: authCtx.userId },
        data: {
            zipCode: parsed.data.zipCode ?? null,
            nearbyDistanceMiles: parsed.data.nearbyDistanceMiles ?? null,
        },
        select: {
            zipCode: true,
            nearbyDistanceMiles: true,
        },
    });

    return NextResponse.json({
        data: {
            zipCode: updatedProfile.zipCode,
            nearbyDistanceMiles: updatedProfile.nearbyDistanceMiles,
        },
    });
});
