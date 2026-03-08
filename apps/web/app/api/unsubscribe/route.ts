import jwt from "jsonwebtoken";
import { z } from "zod";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";

const UnsubscribeSchema = z.object({
    token: z.string().min(1, "token is required"),
});

export async function POST(request: Request) {
    let body: unknown;
    try {
        body = await request.json();
    } catch {
        return NextResponse.json(
            { error: "Invalid JSON body" },
            { status: 400 },
        );
    }

    const parsed = UnsubscribeSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
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

        return NextResponse.json({ success: true });
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            return NextResponse.json(
                {
                    error: "This unsubscribe link has expired. Please request a new one.",
                },
                { status: 401 },
            );
        }
        console.log(error);
        return NextResponse.json(
            { error: "Invalid unsubscribe link" },
            { status: 400 },
        );
    }
}
