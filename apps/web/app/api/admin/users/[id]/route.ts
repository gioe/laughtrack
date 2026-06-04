import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const ROLE_OPTIONS = ["admin", "user"] as const;

const AdminUserUpdateSchema = z
    .object({
        name: z.string().trim().max(255).nullable().optional(),
        image: z.string().trim().max(2048).url().nullable().optional(),
        role: z.enum(ROLE_OPTIONS).optional(),
        zipCode: z
            .string()
            .regex(/^\d{5}$/, "zipCode must be a 5-digit US zip code")
            .nullable()
            .optional(),
        nearbyDistanceMiles: z.number().int().positive().nullable().optional(),
        emailShowNotifications: z.boolean().optional(),
        pushShowNotifications: z.boolean().optional(),
        comedianOnboardingCompleted: z.boolean().optional(),
    })
    .strict()
    .superRefine((value, ctx) => {
        if (Object.keys(value).length === 0) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: "At least one field is required",
            });
        }
    });

const USER_FIELDS = ["name", "image"] as const;
const PROFILE_FIELDS = [
    "role",
    "zipCode",
    "nearbyDistanceMiles",
    "emailShowNotifications",
    "pushShowNotifications",
    "comedianOnboardingCompleted",
] as const;

type Patch = z.infer<typeof AdminUserUpdateSchema>;

function pickUserUpdate(patch: Patch): Prisma.UserUpdateInput {
    const data: Prisma.UserUpdateInput = {};
    if (patch.name !== undefined) data.name = patch.name;
    if (patch.image !== undefined) data.image = patch.image;
    return data;
}

function pickProfileUpdate(patch: Patch): Prisma.UserProfileUpdateInput {
    const data: Prisma.UserProfileUpdateInput = {};
    if (patch.role !== undefined) data.role = patch.role;
    if (patch.zipCode !== undefined) data.zipCode = patch.zipCode;
    if (patch.nearbyDistanceMiles !== undefined) {
        data.nearbyDistanceMiles = patch.nearbyDistanceMiles;
    }
    if (patch.emailShowNotifications !== undefined) {
        data.emailShowNotifications = patch.emailShowNotifications;
    }
    if (patch.pushShowNotifications !== undefined) {
        data.pushShowNotifications = patch.pushShowNotifications;
    }
    if (patch.comedianOnboardingCompleted !== undefined) {
        data.comedianOnboardingCompleted = patch.comedianOnboardingCompleted;
    }
    return data;
}

function hasAny<K extends string>(patch: Patch, keys: readonly K[]): boolean {
    return keys.some(
        (key) => (patch as Record<string, unknown>)[key] !== undefined,
    );
}

const userSnapshotSelect = {
    id: true,
    name: true,
    image: true,
    profile: {
        select: {
            id: true,
            role: true,
            zipCode: true,
            nearbyDistanceMiles: true,
            emailShowNotifications: true,
            pushShowNotifications: true,
            comedianOnboardingCompleted: true,
        },
    },
} as const;

export const PATCH = withRequestMetrics(async function PATCH(
    req: NextRequest,
    ctx: { params: Promise<{ id: string }> },
) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const { id } = await ctx.params;
    if (!id || typeof id !== "string") {
        return NextResponse.json({ error: "Invalid user id" }, { status: 400 });
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

    const parsed = AdminUserUpdateSchema.safeParse(payload);
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const patch = parsed.data;
    const touchesUser = hasAny(patch, USER_FIELDS);
    const touchesProfile = hasAny(patch, PROFILE_FIELDS);

    try {
        const result = await db.$transaction(async (tx) => {
            const before = await tx.user.findUnique({
                where: { id },
                select: userSnapshotSelect,
            });
            if (!before) {
                throw new Prisma.PrismaClientKnownRequestError(
                    "User not found",
                    {
                        code: "P2025",
                        clientVersion: Prisma.prismaVersion.client,
                    },
                );
            }
            if (touchesProfile && !before.profile) {
                return { profileMissing: true as const };
            }

            if (touchesUser) {
                await tx.user.update({
                    where: { id },
                    data: pickUserUpdate(patch),
                });
            }
            if (touchesProfile && before.profile) {
                await tx.userProfile.update({
                    where: { id: before.profile.id },
                    data: pickProfileUpdate(patch),
                });
            }

            const after = await tx.user.findUnique({
                where: { id },
                select: userSnapshotSelect,
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "user.update",
                entityType: "user",
                entityId: id,
                reason: null,
                before: before as unknown as Prisma.InputJsonValue,
                after: after as unknown as Prisma.InputJsonValue,
            });

            return { profileMissing: false as const, user: after };
        });

        if (result.profileMissing) {
            return NextResponse.json(
                { error: "User has no profile; profile fields cannot be set" },
                { status: 422 },
            );
        }

        return NextResponse.json({ ok: true, user: result.user });
    } catch (error) {
        const code = (error as { code?: string })?.code;
        if (code === "P2025") {
            return NextResponse.json(
                { error: "User not found" },
                { status: 404 },
            );
        }
        console.error("Admin user PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});
