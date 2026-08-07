import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import {
    parseDiscoveryRailPolicy,
    type DiscoveryPlatform,
    type DiscoveryRailPolicyDto,
} from "@/lib/discovery/railPolicy";

type RailPolicyRow = Prisma.DiscoveryRailPlatformPolicyGetPayload<{
    include: { entries: true };
}>;

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

export async function getDiscoveryRailPolicy(
    platform: DiscoveryPlatform,
): Promise<DiscoveryRailPolicyDto> {
    const row = await db.discoveryRailPlatformPolicy.findUnique({
        where: { platform },
        include: { entries: true },
    });

    if (!row) {
        throw new Error(`No discovery rail policy found for ${platform}`);
    }

    return toPolicyDto(row);
}
