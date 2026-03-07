import { resolveAuth } from "@/lib/auth/resolveAuth";
import { NextRequest } from "next/server";

export async function getProfileId(req: NextRequest): Promise<string | null> {
    const ctx = await resolveAuth(req);
    return ctx?.profileId ?? null;
}
