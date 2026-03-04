import { db } from "@/lib/db";
import { verifyToken } from "@/util/token";
import { NextRequest } from "next/server";

export async function getProfileId(req: NextRequest): Promise<string | null> {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) return null;
    try {
        const decoded = verifyToken(authHeader.slice(7));
        const profile = await db.userProfile.findFirst({
            where: { user: { email: decoded.email } },
            select: { id: true },
        });
        return profile?.id ?? null;
    } catch (error) {
        console.warn("Bearer token auth failed:", error instanceof Error ? error.message : error);
        return null;
    }
}
