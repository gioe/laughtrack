import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { writeAdminActionAudit } from "@/lib/admin/audit";
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

const CLUB_STATUS_OPTIONS = ["active", "closed", "hiatus"] as const;
const CLUB_TYPE_OPTIONS = ["club", "festival", "venue"] as const;

const statusOverrideSchema = z
    .object({
        name: z.string().trim().min(1).max(255).optional(),
        status: z.enum(CLUB_STATUS_OPTIONS).optional(),
        visible: z.boolean().optional(),
        clubType: z.enum(CLUB_TYPE_OPTIONS).optional(),
        closedAt: z.string().date().nullable().optional(),
    })
    .strict()
    .superRefine((value, ctx) => {
        if (
            value.status === undefined &&
            value.visible === undefined &&
            value.clubType === undefined &&
            value.closedAt === undefined &&
            value.name === undefined
        ) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: "At least one status field is required",
            });
        }
    });

const mutationSchema = z.union([bodySchema, statusOverrideSchema]);

function isStatusOverride(
    value: z.infer<typeof mutationSchema>,
): value is z.infer<typeof statusOverrideSchema> {
    return (
        "name" in value ||
        "status" in value ||
        "visible" in value ||
        "clubType" in value ||
        "closedAt" in value
    );
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

const adminClubSelect = {
    id: true,
    name: true,
    city: true,
    state: true,
    website: true,
    visible: true,
    status: true,
    clubType: true,
    closedAt: true,
    totalShows: true,
    description: true,
    hours: true,
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

export async function PATCH(
    req: NextRequest,
    ctx: { params: Promise<{ id: string }> },
) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

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

    const parsed = mutationSchema.safeParse(payload);
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    try {
        const result = await db.$transaction(async (tx) => {
            const before = await tx.club.findUnique({
                where: { id },
                select: {
                    id: true,
                    name: true,
                    city: true,
                    state: true,
                    website: true,
                    visible: true,
                    status: true,
                    clubType: true,
                    closedAt: true,
                    totalShows: true,
                    description: true,
                    hours: true,
                    chain: {
                        select: {
                            id: true,
                            name: true,
                            slug: true,
                            website: true,
                        },
                    },
                    scrapingSources: adminClubSelect.scrapingSources,
                    shows: adminClubSelect.shows,
                    _count: adminClubSelect._count,
                },
            });
            if (!before) {
                throw new Prisma.PrismaClientKnownRequestError(
                    "Club not found",
                    {
                        code: "P2025",
                        clientVersion: Prisma.prismaVersion.client,
                    },
                );
            }

            const data: Prisma.ClubUpdateInput = {};
            let action = "club.update";

            if (isStatusOverride(parsed.data)) {
                action =
                    parsed.data.name !== undefined &&
                    parsed.data.status === undefined &&
                    parsed.data.visible === undefined &&
                    parsed.data.clubType === undefined &&
                    parsed.data.closedAt === undefined
                        ? "club.update"
                        : "club.status_override";
                if (parsed.data.name !== undefined) {
                    data.name = parsed.data.name.trim().replace(/\s+/g, " ");
                }
                if (parsed.data.status !== undefined) {
                    data.status = parsed.data.status;
                }
                if (parsed.data.visible !== undefined) {
                    data.visible = parsed.data.visible;
                }
                if (parsed.data.clubType !== undefined) {
                    data.clubType = parsed.data.clubType;
                }
                if (parsed.data.closedAt !== undefined) {
                    data.closedAt = parsed.data.closedAt
                        ? new Date(`${parsed.data.closedAt}T00:00:00.000Z`)
                        : null;
                }
            } else {
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

                data.description = normalizedDescription;
                data.hours = hoursToWrite ?? Prisma.DbNull;
            }

            const after = await tx.club.update({
                where: { id },
                data,
                select: adminClubSelect,
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action,
                entityType: "club",
                entityId: id,
                reason: null,
                before,
                after,
            });

            return { beforeName: before.name, club: after };
        });

        revalidateTag("club-detail-data");
        revalidateTag("club-metadata");
        if (result.beforeName !== result.club.name) {
            revalidateTag(result.beforeName);
        }
        revalidateTag(result.club.name);

        return NextResponse.json({
            ok: true,
            club: serializeClubForAdmin(result.club),
        });
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
