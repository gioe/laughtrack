import { auth } from "@/auth";
import { db } from "@/lib/db";
import type { Session } from "next-auth";
import { NextResponse } from "next/server";

export type AdminContext = { userId: string; profileId: string };

async function getCurrentUserProfile(session: Session | null) {
    if (!session?.profile) return null;

    return db.userProfile.findFirst({
        where: {
            OR: [
                { id: session.profile.id },
                { userid: session.profile.userid },
            ],
        },
        select: {
            id: true,
            userid: true,
            role: true,
        },
    });
}

export async function requireAdminForApi(): Promise<
    { ok: true; context: AdminContext } | { ok: false; response: NextResponse }
> {
    const session = await auth();
    if (!session) {
        return {
            ok: false,
            response: NextResponse.json(
                { error: "Unauthorized" },
                { status: 401 },
            ),
        };
    }
    if (!session.profile) {
        return {
            ok: false,
            response: NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422 },
            ),
        };
    }
    const profile = await getCurrentUserProfile(session);
    if (!profile) {
        return {
            ok: false,
            response: NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422 },
            ),
        };
    }
    if (profile.role !== "admin") {
        return {
            ok: false,
            response: NextResponse.json(
                { error: "Forbidden" },
                { status: 403 },
            ),
        };
    }
    return {
        ok: true,
        context: {
            userId: profile.userid,
            profileId: profile.id,
        },
    };
}

export async function isAdminSession(): Promise<boolean> {
    const session = await auth();
    const profile = await getCurrentUserProfile(session);
    return profile?.role === "admin";
}
