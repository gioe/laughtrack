import { auth } from "@/auth";
import { generateToken } from "@/util/token";
import { NextResponse } from "next/server";

/**
 * POST /api/v1/auth/token
 * Exchanges a valid NextAuth session cookie for a short-lived JWT Bearer token.
 * iOS clients can use this after completing OAuth via ASWebAuthenticationSession.
 */
export async function POST() {
    const session = await auth();
    if (!session?.user?.email) {
        return new NextResponse(null, { status: 401 });
    }

    const token = generateToken({ email: session.user.email }, "access");
    return NextResponse.json({ token });
}
