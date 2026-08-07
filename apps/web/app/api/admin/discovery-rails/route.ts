import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import {
    DISCOVERY_PLATFORMS,
    DISCOVERY_RAIL_CATALOG_VERSION,
    DiscoveryRailPolicyUpdateSchema,
    getDefaultDiscoveryRailPolicy,
    parseDiscoveryRailPolicy,
    type DiscoveryPlatform,
    type DiscoveryRailPolicyDto,
} from "@/lib/discovery/railPolicy";
import { withRequestMetrics } from "@/lib/metrics";
import { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";

type RailPolicyRow = Prisma.DiscoveryRailPlatformPolicyGetPayload<{
    include: { entries: true };
}>;

type AdminRailPolicyRow = Prisma.DiscoveryRailPlatformPolicyGetPayload<{
    include: {
        entries: true;
        updatedByProfile: {
            select: {
                id: true;
                user: { select: { name: true; email: true } };
            };
        };
    };
}>;

type RailPolicyWriter = Pick<
    Prisma.TransactionClient,
    | "discoveryRailPlatformPolicy"
    | "discoveryRailPolicyEntry"
    | "adminActionAudit"
>;

class RailPolicyVersionConflict extends Error {
    constructor(
        readonly platform: DiscoveryPlatform,
        readonly expectedVersion: number,
        readonly currentVersion: number,
    ) {
        super(`Discovery rail policy for ${platform} has changed`);
    }
}

async function readBody(req: NextRequest): Promise<unknown> {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function toPolicyDto(row: RailPolicyRow): DiscoveryRailPolicyDto {
    return parseDiscoveryRailPolicy({
        platform: row.platform,
        catalogVersion: row.catalogVersion,
        version: row.policyVersion,
        cycleCadenceHours: row.cycleCadenceHours,
        rails: row.entries
            .map((entry) => ({
                railKey: entry.railKey,
                enabled: entry.enabled,
                position: entry.position,
                rotationPool: entry.rotationPool,
                weight: entry.weight,
            }))
            .sort(
                (left, right) =>
                    left.position - right.position ||
                    left.railKey.localeCompare(right.railKey),
            ),
    });
}

function toAdminPolicyDto(row: AdminRailPolicyRow) {
    return {
        ...toPolicyDto(row),
        provenance: "stored" as const,
        updatedAt: row.updatedAt.toISOString(),
        updatedBy: row.updatedByProfile
            ? {
                  profileId: row.updatedByProfile.id,
                  name: row.updatedByProfile.user.name,
                  email: row.updatedByProfile.user.email,
              }
            : null,
    };
}

export const GET = withRequestMetrics(async function GET() {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    try {
        const [catalog, policyRows] = await db.$transaction(
            async (tx) =>
                Promise.all([
                    tx.discoveryRailCatalog.findMany({
                        where: {
                            catalogVersion: {
                                lte: DISCOVERY_RAIL_CATALOG_VERSION,
                            },
                        },
                        orderBy: { key: "asc" },
                        select: {
                            key: true,
                            label: true,
                            contentKind: true,
                            requiresAuth: true,
                            supportedPlatforms: true,
                            catalogVersion: true,
                        },
                    }),
                    tx.discoveryRailPlatformPolicy.findMany({
                        include: {
                            entries: true,
                            updatedByProfile: {
                                select: {
                                    id: true,
                                    user: {
                                        select: { name: true, email: true },
                                    },
                                },
                            },
                        },
                    }),
                ]),
            {
                isolationLevel: Prisma.TransactionIsolationLevel.RepeatableRead,
            },
        );

        const byPlatform = new Map(
            policyRows.map((row) => [row.platform, row]),
        );
        const platforms = DISCOVERY_PLATFORMS.map((platform) => {
            const row = byPlatform.get(platform);
            return row
                ? toAdminPolicyDto(row)
                : {
                      ...getDefaultDiscoveryRailPolicy(platform),
                      provenance: "built_in_default" as const,
                      updatedAt: null,
                      updatedBy: null,
                  };
        });

        return NextResponse.json({
            catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
            catalog,
            platforms,
        });
    } catch (error) {
        console.error("Admin discovery rails GET failed:", error);
        return NextResponse.json(
            { error: "Unable to load discovery rail policies" },
            { status: 500 },
        );
    }
});

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const parsed = DiscoveryRailPolicyUpdateSchema.safeParse(
        await readBody(req),
    );
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const input = parsed.data;
    try {
        const policy = await db.$transaction(async (tx: RailPolicyWriter) => {
            const current = await tx.discoveryRailPlatformPolicy.findUnique({
                where: { platform: input.platform },
                include: { entries: true },
            });
            const currentVersion = current?.policyVersion ?? 0;
            if (!current || currentVersion !== input.expectedVersion) {
                throw new RailPolicyVersionConflict(
                    input.platform,
                    input.expectedVersion,
                    currentVersion,
                );
            }

            const updated = await tx.discoveryRailPlatformPolicy.updateMany({
                where: {
                    platform: input.platform,
                    policyVersion: input.expectedVersion,
                },
                data: {
                    policyVersion: { increment: 1 },
                    catalogVersion: input.catalogVersion,
                    cycleCadenceHours: input.cycleCadenceHours,
                    updatedByProfileId: gate.context.profileId,
                },
            });
            if (updated.count !== 1) {
                const latest = await tx.discoveryRailPlatformPolicy.findUnique({
                    where: { platform: input.platform },
                    select: { policyVersion: true },
                });
                throw new RailPolicyVersionConflict(
                    input.platform,
                    input.expectedVersion,
                    latest?.policyVersion ?? 0,
                );
            }

            await tx.discoveryRailPolicyEntry.deleteMany({
                where: { platform: input.platform },
            });
            await tx.discoveryRailPolicyEntry.createMany({
                data: input.rails.map((rail) => ({
                    platform: input.platform,
                    railKey: rail.railKey,
                    enabled: rail.enabled,
                    position: rail.position,
                    rotationPool: rail.rotationPool,
                    weight: rail.weight,
                })),
            });

            const before = toPolicyDto(current);
            const after = parseDiscoveryRailPolicy({
                platform: input.platform,
                catalogVersion: input.catalogVersion,
                version: input.expectedVersion + 1,
                cycleCadenceHours: input.cycleCadenceHours,
                rails: input.rails,
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: gate.context.profileId,
                action: "discovery_rail_policy.update",
                entityType: "discovery_rail_policy",
                entityId: input.platform,
                before: JSON.parse(JSON.stringify(before)),
                after: JSON.parse(JSON.stringify(after)),
            });

            return after;
        });

        return NextResponse.json({ ok: true, policy });
    } catch (error) {
        if (error instanceof RailPolicyVersionConflict) {
            return NextResponse.json(
                {
                    error: error.message,
                    platform: error.platform,
                    expectedVersion: error.expectedVersion,
                    currentVersion: error.currentVersion,
                },
                { status: 409 },
            );
        }

        console.error("Admin discovery rails PATCH failed:", error);
        return NextResponse.json(
            { error: "Unable to update discovery rail policy" },
            { status: 500 },
        );
    }
});
