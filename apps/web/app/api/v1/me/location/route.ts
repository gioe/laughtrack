import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";

const ProfileLocationUpdateSchema = z.object({
    zip_code: z
        .string()
        .regex(/^\d{5}$/, "zip_code must be a 5-digit US zip code")
        .nullable(),
    nearby_distance_miles: z.number().int().positive().nullable(),
});

export async function PATCH(req: NextRequest) {
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
            zipCode: parsed.data.zip_code,
            nearbyDistanceMiles: parsed.data.nearby_distance_miles,
        },
        select: {
            zipCode: true,
            nearbyDistanceMiles: true,
        },
    });

    return NextResponse.json({
        data: {
            zip_code: updatedProfile.zipCode,
            nearby_distance_miles: updatedProfile.nearbyDistanceMiles,
        },
    });
}
