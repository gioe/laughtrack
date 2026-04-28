import { auth } from "@/auth";
import { db } from "@/lib/db";
import { verifyToken } from "@/util/token";
import { NextRequest } from "next/server";

export interface AuthContext {
    profileId: string;
    userId: string;
    role?: string;
}

/** Sentinel returned when the user IS authenticated but has no UserProfile row. */
export const PROFILE_MISSING = "PROFILE_MISSING" as const;
export type ProfileMissing = typeof PROFILE_MISSING;

/**
 * Resolves the authenticated user from a request.
 * Tries Bearer token first, then falls back to NextAuth session cookie.
 * Returns null if not authenticated.
 * Returns PROFILE_MISSING if authenticated but UserProfile row is absent.
 */
export async function resolveAuth(
    req: NextRequest,
): Promise<AuthContext | ProfileMissing | null> {
    const authHeader = req.headers.get("Authorization");
    if (authHeader?.startsWith("Bearer ")) {
        try {
            const decoded = verifyToken(authHeader.slice(7));
            const user = await db.user.findUnique({
                where: { email: decoded.email },
                select: {
                    id: true,
                    profile: { select: { id: true, role: true } },
                },
            });
            if (!user) return null;
            if (!user.profile?.id) return PROFILE_MISSING;
            return {
                profileId: user.profile.id,
                userId: user.id,
                role: user.profile.role,
            };
        } catch (error) {
            console.warn(
                "Bearer token auth failed:",
                error instanceof Error ? error.message : error,
            );
            return null;
        }
    }

    const session = await auth();
    if (!session) return null;
    if (!session.profile?.id || !session.profile?.userid)
        return PROFILE_MISSING;
    return {
        profileId: session.profile.id,
        userId: session.profile.userid,
        role: session.profile.role,
    };
}
