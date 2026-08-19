import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

const IDENTITY_SELECT = {
    id: true,
    uuid: true,
    visible: true,
    parentComedianId: true,
} satisfies Prisma.ComedianSelect;

type IdentityRow = Prisma.ComedianGetPayload<{
    select: typeof IDENTITY_SELECT;
}>;

export interface CanonicalComedianIdentity {
    rootId: number;
    rootUuid: string;
    memberUuids: string[];
}

export async function resolveCanonicalComedianIdentityById(
    comedianId: number,
): Promise<CanonicalComedianIdentity | null> {
    const seed = await db.comedian.findUnique({
        where: { id: comedianId },
        select: IDENTITY_SELECT,
    });

    if (!seed?.visible) return null;
    return resolveCanonicalComedianIdentity(seed);
}

export async function resolveCanonicalComedianIdentityByName(
    name: string,
): Promise<CanonicalComedianIdentity | null> {
    const seed = await db.comedian.findFirst({
        where: {
            name: {
                equals: name,
                mode: Prisma.QueryMode.insensitive,
            },
            visible: true,
        },
        select: IDENTITY_SELECT,
        orderBy: { id: "asc" },
    });

    if (!seed) return null;
    return resolveCanonicalComedianIdentity(seed);
}

async function resolveCanonicalComedianIdentity(
    seed: IdentityRow,
): Promise<CanonicalComedianIdentity | null> {
    const ancestorIds = new Set<number>();
    let root = seed;

    while (true) {
        if (ancestorIds.has(root.id)) return null;
        ancestorIds.add(root.id);

        if (root.parentComedianId === null) break;
        const parent = await db.comedian.findUnique({
            where: { id: root.parentComedianId },
            select: IDENTITY_SELECT,
        });
        if (!parent) return null;
        root = parent;
    }

    if (!root.visible) return null;

    const memberIds = new Set<number>([root.id]);
    const memberUuids = [root.uuid];
    let frontierIds = [root.id];

    while (frontierIds.length > 0) {
        const children = await db.comedian.findMany({
            where: { parentComedianId: { in: frontierIds } },
            select: IDENTITY_SELECT,
            orderBy: { id: "asc" },
        });
        const nextFrontierIds: number[] = [];

        for (const child of children) {
            if (memberIds.has(child.id)) continue;
            memberIds.add(child.id);
            memberUuids.push(child.uuid);
            nextFrontierIds.push(child.id);
        }

        frontierIds = nextFrontierIds;
    }

    return {
        rootId: root.id,
        rootUuid: root.uuid,
        memberUuids,
    };
}
