import { auth } from "@/auth";
import { db } from "@/lib/db";
import { verifyToken } from "@/util/token";
import { NextRequest } from "next/server";

export interface AuthContext {
    profileId: string;
    userId: string;
}

/**
 * Resolves the authenticated user from a request.
 * Tries Bearer token first, then falls back to NextAuth session cookie.
 * Returns null if neither is present or valid.
 */
export async function resolveAuth(
    req: NextRequest,
): Promise<AuthContext | null> {
    const authHeader = req.headers.get("Authorization");
    if (authHeader?.startsWith("Bearer ")) {
        try {
            const decoded = verifyToken(authHeader.slice(7));
            const user = await db.user.findUnique({
                where: { email: decoded.email },
                select: { id: true, profile: { select: { id: true } } },
            });
            if (user?.profile?.id) {
                return { profileId: user.profile.id, userId: user.id };
            }
            return null;
        } catch (error) {
            console.warn(
                "Bearer token auth failed:",
                error instanceof Error ? error.message : error,
            );
            return null;
        }
    }

    const session = await auth();
    if (!session?.profile?.id || !session?.profile?.userid) return null;
    return { profileId: session.profile.id, userId: session.profile.userid };
}
