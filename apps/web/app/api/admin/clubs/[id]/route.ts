import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { NextRequest, NextResponse } from "next/server";
import { revalidateTag } from "next/cache";
import { z } from "zod";

const DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
] as const;

const hoursSchema = z
    .object(
        Object.fromEntries(DAYS.map((d) => [d, z.string().max(64)])) as Record<
            (typeof DAYS)[number],
            z.ZodString
        >,
    )
    .strict();

const bodySchema = z.object({
    description: z.string().max(5000).nullable(),
    hours: hoursSchema.nullable(),
});

export async function PATCH(
    req: NextRequest,
    ctx: { params: Promise<{ id: string }> },
) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const { id: idParam } = await ctx.params;
    const id = Number(idParam);
    if (!Number.isInteger(id) || id <= 0) {
        return NextResponse.json({ error: "Invalid club id" }, { status: 400 });
    }

    let payload: unknown;
    try {
        payload = await req.json();
    } catch {
        return NextResponse.json(
            { error: "Body must be valid JSON" },
            { status: 400 },
        );
    }

    const parsed = bodySchema.safeParse(payload);
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const { description, hours } = parsed.data;

    const normalizedDescription =
        description === null ? null : description.trim() || null;

    const normalizedHours = hours
        ? Object.fromEntries(
              Object.entries(hours)
                  .map(([day, val]) => [day, val.trim()])
                  .filter(([, val]) => val !== ""),
          )
        : null;
    const hoursToWrite =
        normalizedHours && Object.keys(normalizedHours).length > 0
            ? normalizedHours
            : null;

    try {
        const updated = await db.club.update({
            where: { id },
            data: {
                description: normalizedDescription,
                hours: hoursToWrite ?? Prisma.DbNull,
            },
            select: { id: true, name: true },
        });

        revalidateTag("club-detail-data");
        revalidateTag("club-metadata");
        revalidateTag(updated.name);

        return NextResponse.json({ ok: true, club: updated });
    } catch (error) {
        const code = (error as { code?: string })?.code;
        if (code === "P2025") {
            return NextResponse.json(
                { error: "Club not found" },
                { status: 404 },
            );
        }
        console.error("Admin club PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
}
