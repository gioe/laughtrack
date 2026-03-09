import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { NextRequest } from "next/server";

export async function getProfileId(req: NextRequest): Promise<string | null> {
    const ctx = await resolveAuth(req);
    if (!ctx || ctx === PROFILE_MISSING) return null;
    return ctx.profileId;
}
