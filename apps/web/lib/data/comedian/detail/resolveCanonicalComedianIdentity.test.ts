import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findUnique: vi.fn(),
            findFirst: vi.fn(),
            findMany: vi.fn(),
        },
    },
}));

import { db } from "@/lib/db";
import {
    resolveCanonicalComedianIdentityById,
    resolveCanonicalComedianIdentityByName,
} from "./resolveCanonicalComedianIdentity";

type IdentityRow = {
    id: number;
    uuid: string;
    visible: boolean;
    parentComedianId: number | null;
};

const mockFindUnique = vi.mocked(db.comedian.findUnique as any);
const mockFindFirst = vi.mocked(db.comedian.findFirst as any);
const mockFindMany = vi.mocked(db.comedian.findMany as any);

function mockIdentityGraph(rows: IdentityRow[]) {
    const byId = new Map(rows.map((row) => [row.id, row]));
    mockFindUnique.mockImplementation(async (args: any) => {
        return (byId.get(args.where.id!) ?? null) as never;
    });
    mockFindMany.mockImplementation(async (args: any) => {
        const parentIds = (args?.where?.parentComedianId as { in: number[] })
            .in;
        return rows.filter((row) =>
            row.parentComedianId === null
                ? false
                : parentIds.includes(row.parentComedianId),
        ) as never;
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("resolveCanonicalComedianIdentity", () => {
    it("ascends to the root and collects direct and deeper descendants", async () => {
        const rows: IdentityRow[] = [
            {
                id: 854864,
                uuid: "jesus-root",
                visible: true,
                parentComedianId: null,
            },
            {
                id: 332627,
                uuid: "jesus-child",
                visible: true,
                parentComedianId: 854864,
            },
            {
                id: 246800,
                uuid: "jesus-grandchild",
                visible: false,
                parentComedianId: 332627,
            },
        ];
        mockIdentityGraph(rows);

        await expect(
            resolveCanonicalComedianIdentityById(332627),
        ).resolves.toEqual({
            rootId: 854864,
            rootUuid: "jesus-root",
            memberUuids: ["jesus-root", "jesus-child", "jesus-grandchild"],
        });
    });

    it("uses exact case-insensitive name matching and includes hidden descendants", async () => {
        const rows: IdentityRow[] = [
            {
                id: 1,
                uuid: "canonical",
                visible: true,
                parentComedianId: null,
            },
            {
                id: 2,
                uuid: "hidden-alias",
                visible: false,
                parentComedianId: 1,
            },
        ];
        mockIdentityGraph(rows);
        mockFindFirst.mockResolvedValue(rows[0] as never);

        const result =
            await resolveCanonicalComedianIdentityByName("Chris D'Elia");

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    name: {
                        equals: "Chris D'Elia",
                        mode: "insensitive",
                    },
                    visible: true,
                },
            }),
        );
        expect(result?.memberUuids).toEqual(["canonical", "hidden-alias"]);
    });

    it("fails closed for hidden requested rows, missing parents, and cycles", async () => {
        mockFindUnique.mockResolvedValueOnce({
            id: 1,
            uuid: "hidden",
            visible: false,
            parentComedianId: null,
        } as never);
        await expect(
            resolveCanonicalComedianIdentityById(1),
        ).resolves.toBeNull();

        mockIdentityGraph([
            {
                id: 2,
                uuid: "orphan",
                visible: true,
                parentComedianId: 99,
            },
        ]);
        await expect(
            resolveCanonicalComedianIdentityById(2),
        ).resolves.toBeNull();

        mockIdentityGraph([
            {
                id: 3,
                uuid: "cycle-a",
                visible: true,
                parentComedianId: 4,
            },
            {
                id: 4,
                uuid: "cycle-b",
                visible: true,
                parentComedianId: 3,
            },
        ]);
        await expect(
            resolveCanonicalComedianIdentityById(3),
        ).resolves.toBeNull();
    });
});
