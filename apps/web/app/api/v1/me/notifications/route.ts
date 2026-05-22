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

const NotificationPreferenceUpdateSchema = z
    .object({
        emailShowNotifications: z.boolean().optional(),
        pushShowNotifications: z.boolean().optional(),
    })
    .refine(
        (data) =>
            data.emailShowNotifications !== undefined ||
            data.pushShowNotifications !== undefined,
        {
            message: "At least one notification preference must be provided",
        },
    );

export async function PATCH(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-notifications-ip:${getClientIp(req)}`,
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
        `me-notifications:${authCtx.userId}`,
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

    const parsed = NotificationPreferenceUpdateSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
        );
    }

    const updatedProfile = await db.userProfile.update({
        where: { userid: authCtx.userId },
        data: {
            emailShowNotifications: parsed.data.emailShowNotifications,
            pushShowNotifications: parsed.data.pushShowNotifications,
        },
        select: {
            emailShowNotifications: true,
            pushShowNotifications: true,
        },
    });

    return NextResponse.json({
        data: {
            emailShowNotifications: updatedProfile.emailShowNotifications,
            pushShowNotifications: updatedProfile.pushShowNotifications,
        },
    });
}
