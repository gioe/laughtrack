import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const clubCreateSchema = z
    .object({
        name: z.string().trim().min(1).max(255),
        address: z.string().trim().min(1).max(500),
        website: z.string().trim().url().max(2000),
    })
    .strict();

const adminClubSelect = {
    id: true,
    name: true,
    address: true,
    city: true,
    state: true,
    website: true,
    visible: true,
    status: true,
    clubType: true,
    closedAt: true,
    totalShows: true,
    chain: { select: { id: true, name: true, slug: true, website: true } },
    scrapingSources: {
        select: {
            id: true,
            platform: true,
            scraperKey: true,
            enabled: true,
            priority: true,
        },
        orderBy: [{ priority: "asc" as const }, { id: "asc" as const }],
    },
    shows: {
        select: {
            lastScrapedDate: true,
            lastScrapedBy: true,
        },
        orderBy: [
            { lastScrapedDate: "desc" as const },
            { id: "desc" as const },
        ],
        take: 1,
    },
    _count: { select: { shows: true } },
};

function normalizeText(value: string) {
    return value.trim().replace(/\s+/g, " ");
}

function serializeClubForAdmin(club: {
    id: number;
    name: string;
    city: string | null;
    state: string | null;
    website: string;
    visible: boolean | null;
    status: string;
    clubType: string;
    closedAt: Date | null;
    totalShows: number;
    chain: {
        id: number;
        name: string;
        slug: string;
        website: string | null;
    } | null;
    scrapingSources: Array<{
        id: number;
        platform: string;
        scraperKey: string;
        enabled: boolean;
        priority: number;
    }>;
    shows: Array<{
        lastScrapedDate: Date | null;
        lastScrapedBy: string | null;
    }>;
    _count: { shows: number };
}) {
    const latestShow = club.shows[0] ?? null;
    return {
        id: club.id,
        name: club.name,
        city: club.city,
        state: club.state,
        website: club.website,
        visible: club.visible ?? true,
        status: club.status,
        clubType: club.clubType,
        closedAt: club.closedAt?.toISOString() ?? null,
        totalShows: club.totalShows,
        scrapedShowCount: club._count.shows,
        latestScrapeAt: latestShow?.lastScrapedDate?.toISOString() ?? null,
        latestScrapeBy: latestShow?.lastScrapedBy ?? null,
        scrapingSources: club.scrapingSources,
        chain: club.chain,
    };
}

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = clubCreateSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const data = {
        name: normalizeText(parsed.data.name),
        address: normalizeText(parsed.data.address),
        website: parsed.data.website.trim(),
    };

    try {
        const club = await db.$transaction(async (tx) => {
            const created = await tx.club.create({
                data,
                select: adminClubSelect,
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "club.create",
                entityType: "club",
                entityId: created.id,
                reason: null,
                before: {},
                after: created,
            });

            return created;
        });

        revalidateTag("club-detail-data");
        revalidateTag("club-metadata");
        revalidateTag(club.name);

        return NextResponse.json(
            { ok: true, club: serializeClubForAdmin(club) },
            { status: 201 },
        );
    } catch (error) {
        if (
            error instanceof Prisma.PrismaClientKnownRequestError &&
            error.code === "P2002"
        ) {
            return NextResponse.json(
                { error: "A club with that name already exists" },
                { status: 409 },
            );
        }

        console.error("Admin club POST failed:", error);
        return NextResponse.json({ error: "Create failed" }, { status: 500 });
    }
}
