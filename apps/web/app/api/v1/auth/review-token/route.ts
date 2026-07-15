import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { verifyReviewPassword } from "@/lib/auth/reviewCredentials";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";
import { withRequestMetrics } from "@/lib/metrics";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { ACCESS_TOKEN_TTL_SECONDS, generateAccessToken } from "@/util/token";

type ReviewTokenRequest = {
    email?: unknown;
    password?: unknown;
};

const NO_STORE_HEADERS = { "Cache-Control": "no-store" };

function reviewConfiguration() {
    const email = process.env.APP_REVIEW_EMAIL?.trim().toLowerCase() ?? "";
    const passwordHash = process.env.APP_REVIEW_PASSWORD_HASH?.trim() ?? "";
    return email && passwordHash ? { email, passwordHash } : null;
}

/**
 * POST /api/v1/auth/review-token
 *
 * Exchanges the single allowlisted store-review credential for the same
 * access/refresh token pair used by normal native OAuth. There is deliberately
 * no public password registration or password column: the credential is scoped
 * to one environment-configured account and stored only as a scrypt hash.
 */
export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-review-token:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const config = reviewConfiguration();
    if (!config) {
        return new NextResponse(null, {
            status: 404,
            headers: NO_STORE_HEADERS,
        });
    }

    const origin = req.headers.get("origin");
    if (origin && origin !== req.nextUrl.origin) {
        return new NextResponse(null, {
            status: 403,
            headers: NO_STORE_HEADERS,
        });
    }

    let body: ReviewTokenRequest;
    try {
        body = (await req.json()) as ReviewTokenRequest;
    } catch {
        return NextResponse.json(
            { error: "invalid_credentials" },
            {
                status: 401,
                headers: { ...rateLimitHeaders(rl), ...NO_STORE_HEADERS },
            },
        );
    }

    const email =
        typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    const password = typeof body.password === "string" ? body.password : "";
    const passwordMatches = verifyReviewPassword(password, config.passwordHash);

    if (email !== config.email || !passwordMatches) {
        return NextResponse.json(
            { error: "invalid_credentials" },
            {
                status: 401,
                headers: { ...rateLimitHeaders(rl), ...NO_STORE_HEADERS },
            },
        );
    }

    // Re-create the account if a reviewer exercises account deletion, and
    // ensure older manually-created review users have the required profile.
    const user = await db.user.upsert({
        where: { email: config.email },
        create: {
            email: config.email,
            emailVerified: new Date(),
            name: "App Review",
            profile: {
                create: {
                    role: "user",
                    comedianOnboardingCompleted: true,
                    zipCode: "10001",
                    nearbyDistanceMiles: 25,
                },
            },
        },
        update: {
            profile: {
                upsert: {
                    create: {
                        role: "user",
                        comedianOnboardingCompleted: true,
                        zipCode: "10001",
                        nearbyDistanceMiles: 25,
                    },
                    update: {},
                },
            },
        },
        select: { id: true, email: true },
    });

    const accessToken = generateAccessToken({ email: user.email });
    const { token: refreshToken } = await issueRefreshToken(user.id);

    return NextResponse.json(
        {
            accessToken,
            refreshToken,
            expiresIn: ACCESS_TOKEN_TTL_SECONDS,
        },
        {
            headers: { ...rateLimitHeaders(rl), ...NO_STORE_HEADERS },
        },
    );
});
