import jwt from "jsonwebtoken";
import { z } from "zod";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

const UnsubscribeSchema = z.object({
    token: z.string().min(1, "token is required"),
});

export async function POST(request: NextRequest) {
    const rl = checkRateLimit(
        `unsubscribe:${getClientIp(request)}`,
        RATE_LIMITS.unsubscribe,
    );
    if (!rl.allowed) {
        return rateLimitResponse(rl);
    }

    let body: unknown;
    try {
        body = await request.json();
    } catch {
        return NextResponse.json(
            { error: "Invalid JSON body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const parsed = UnsubscribeSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const { token } = parsed.data;
    try {
        // Verify token - this will throw an error if token is invalid or expired
        const decoded = jwt.verify(token, process.env.SECRET_KEY!) as {
            email: string;
            type: string;
            exp: number;
            iat: number;
        };
        // Token is valid! We can trust that this request is from the owner of this email
        const userEmail = decoded.email;

        // Update the database
        await db.user.update({
            where: {
                email: userEmail,
            },
            data: {
                profile: {
                    update: {
                        emailShowNotifications: false,
                    },
                },
            },
        });

        return NextResponse.json(
            { success: true },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            return NextResponse.json(
                {
                    error: "This unsubscribe link has expired. Please request a new one.",
                },
                { status: 401, headers: rateLimitHeaders(rl) },
            );
        }
        if (error instanceof jwt.JsonWebTokenError) {
            return NextResponse.json(
                { error: "Invalid unsubscribe link" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        console.error(error);
        return NextResponse.json(
            { error: "Failed to process unsubscribe request" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
