import { auth } from "@/auth";
import { NextResponse } from "next/server";

export type AdminContext = { userId: string; profileId: string };

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
    if (session.profile.role !== "admin") {
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
            userId: session.profile.userid,
            profileId: session.profile.id,
        },
    };
}

export async function isAdminSession(): Promise<boolean> {
    const session = await auth();
    return session?.profile?.role === "admin";
}
