import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { createInbox } from "@/lib/admin/curation/inbox";
import { CurationError } from "@/lib/admin/curation/decisions";
export async function GET(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    try {
        return NextResponse.json(
            await createInbox(db).get(
                Object.fromEntries(req.nextUrl.searchParams),
            ),
        );
    } catch (e) {
        if (e instanceof z.ZodError)
            return NextResponse.json(
                { error: "Invalid review filters." },
                { status: 400 },
            );
        if (e instanceof CurationError)
            return NextResponse.json(
                { error: e.message },
                { status: e.status },
            );
        console.error("Curation inbox unavailable", e);
        return NextResponse.json(
            {
                error: "The curation inbox is unavailable. Its database migrations and legacy reconciliation must be completed before review.",
            },
            { status: 503 },
        );
    }
}
