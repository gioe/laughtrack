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

const PushTokenSchema = z.object({
    token: z
        .string()
        .trim()
        .min(16, "token must be at least 16 characters")
        .max(4096, "token must be at most 4096 characters"),
    platform: z.literal("ios").optional().default("ios"),
});

async function authenticate(req: NextRequest, prefix: string) {
    const ipRl = await checkRateLimit(
        `${prefix}-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return { response: rateLimitResponse(ipRl) };

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return {
            response: NextResponse.json(
                { error: "profile_missing" },
                { status: 422 },
            ),
        };
    }
    if (!authCtx) {
        return {
            response: NextResponse.json(
                { error: "unauthorized" },
                { status: 401 },
            ),
        };
    }

    const rl = await checkRateLimit(
        `${prefix}:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return { response: rateLimitResponse(rl) };

    return { authCtx };
}

async function parseBody(req: NextRequest) {
    let body: unknown;
    try {
        body = await req.json();
    } catch {
        return {
            response: NextResponse.json(
                { error: "Invalid JSON body" },
                { status: 400 },
            ),
        };
    }

    const parsed = PushTokenSchema.safeParse(body);
    if (!parsed.success) {
        return {
            response: NextResponse.json(
                { error: parsed.error.errors[0].message },
                { status: 400 },
            ),
        };
    }

    return {
        data: {
            platform: parsed.data.platform,
            token: parsed.data.token.toLowerCase(),
        },
    };
}

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const auth = await authenticate(req, "me-push-token");
    if (auth.response) return auth.response;

    const parsed = await parseBody(req);
    if (parsed.response) return parsed.response;

    const registeredAt = new Date();
    const token = await db.userPushToken.upsert({
        where: { token: parsed.data.token },
        create: {
            token: parsed.data.token,
            platform: parsed.data.platform,
            userId: auth.authCtx.userId,
            profileId: auth.authCtx.profileId,
            isActive: true,
            revokedAt: null,
        },
        update: {
            platform: parsed.data.platform,
            userId: auth.authCtx.userId,
            profileId: auth.authCtx.profileId,
            isActive: true,
            revokedAt: null,
            lastRegisteredAt: registeredAt,
        },
        select: {
            id: true,
            platform: true,
            isActive: true,
        },
    });

    return NextResponse.json({ data: token });
});

export const DELETE = withRequestMetrics(async function DELETE(
    req: NextRequest,
) {
    const auth = await authenticate(req, "me-push-token-delete");
    if (auth.response) return auth.response;

    const parsed = await parseBody(req);
    if (parsed.response) return parsed.response;

    const result = await db.userPushToken.updateMany({
        where: {
            token: parsed.data.token,
            userId: auth.authCtx.userId,
            profileId: auth.authCtx.profileId,
            isActive: true,
        },
        data: {
            isActive: false,
            revokedAt: new Date(),
        },
    });

    return NextResponse.json({ data: { deactivated: result.count > 0 } });
});
