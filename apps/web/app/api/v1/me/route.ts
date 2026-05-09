import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

const ProfileUpdateSchema = z.object({
    comedian_onboarding_completed: z.boolean({
        required_error: "comedian_onboarding_completed is required",
        invalid_type_error: "comedian_onboarding_completed must be a boolean",
    }),
});

export async function GET(req: NextRequest) {
    // Pre-auth IP rate limit protects resolveAuth() / auth() from
    // unauthenticated probes — matches the /auth/signout pattern.
    const ipRl = await checkRateLimit(
        `me-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            { error: "profile_missing" },
            { status: 422, headers: rateLimitHeaders(ipRl) },
        );
    }
    if (!authCtx) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(ipRl) },
        );
    }

    const rl = await checkRateLimit(
        `me:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const user = await db.user.findUnique({
        where: { id: authCtx.userId },
        select: {
            name: true,
            email: true,
            image: true,
            profile: {
                select: {
                    emailShowNotifications: true,
                    pushShowNotifications: true,
                    comedianOnboardingCompleted: true,
                    zipCode: true,
                    nearbyDistanceMiles: true,
                },
            },
        },
    });
    if (!user) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    return NextResponse.json(
        {
            data: {
                display_name: user.name,
                email: user.email,
                avatar_url: user.image,
                email_show_notifications:
                    user.profile?.emailShowNotifications ?? false,
                push_show_notifications:
                    user.profile?.pushShowNotifications ?? false,
                comedian_onboarding_completed:
                    user.profile?.comedianOnboardingCompleted ?? false,
                zip_code: user.profile?.zipCode ?? null,
                nearby_distance_miles:
                    user.profile?.nearbyDistanceMiles ?? null,
            },
        },
        { headers: rateLimitHeaders(rl) },
    );
}

export async function PATCH(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-patch-ip:${getClientIp(req)}`,
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
        `me-patch:${authCtx.userId}`,
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

    const parsed = ProfileUpdateSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
        );
    }

    const updatedProfile = await db.userProfile.update({
        where: { userid: authCtx.userId },
        data: {
            comedianOnboardingCompleted:
                parsed.data.comedian_onboarding_completed,
        },
        select: {
            comedianOnboardingCompleted: true,
        },
    });

    return NextResponse.json({
        data: {
            comedian_onboarding_completed:
                updatedProfile.comedianOnboardingCompleted,
        },
    });
}

export async function DELETE(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-delete-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            { error: "profile_missing" },
            { status: 422, headers: rateLimitHeaders(ipRl) },
        );
    }
    if (!authCtx) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(ipRl) },
        );
    }

    const rl = await checkRateLimit(
        `me-delete:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    try {
        await db.$transaction(async (tx) => {
            await tx.favoriteComedian.deleteMany({
                where: { profileId: authCtx.profileId },
            });
            await tx.userProfile.delete({
                where: { id: authCtx.profileId },
            });
            await tx.user.delete({
                where: { id: authCtx.userId },
            });
        });
    } catch (error) {
        console.error("DELETE /api/v1/me error:", error);
        return NextResponse.json(
            { error: "account_delete_failed" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }

    return NextResponse.json(
        { data: { deleted: true } },
        { headers: rateLimitHeaders(rl) },
    );
}
