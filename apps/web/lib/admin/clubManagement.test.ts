import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    findMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        club: {
            findMany: mocks.findMany,
        },
    },
}));

import { listAdminClubGroups } from "./clubManagement";

function clubRow({
    id,
    name,
    chain,
}: {
    id: number;
    name: string;
    chain: {
        id: number;
        name: string;
        slug: string;
        website: string | null;
    } | null;
}) {
    return {
        id,
        name,
        city: "New York",
        state: "NY",
        website: "https://example.com",
        visible: true,
        status: "active",
        clubType: "club",
        closedAt: null,
        totalShows: 0,
        chain,
        scrapingSources: [],
        shows: [],
        _count: { shows: 0 },
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("listAdminClubGroups", () => {
    it("orders chain groups by club count descending with unchained last", async () => {
        const bigChain = {
            id: 1,
            name: "Big Chain",
            slug: "big-chain",
            website: null,
        };
        const smallChain = {
            id: 2,
            name: "Small Chain",
            slug: "small-chain",
            website: null,
        };
        const tieChain = {
            id: 3,
            name: "Alpha Chain",
            slug: "alpha-chain",
            website: null,
        };

        mocks.findMany.mockResolvedValue([
            clubRow({ id: 1, name: "Small A", chain: smallChain }),
            clubRow({ id: 2, name: "Big A", chain: bigChain }),
            clubRow({ id: 3, name: "Big B", chain: bigChain }),
            clubRow({ id: 4, name: "Unchained A", chain: null }),
            clubRow({ id: 5, name: "Alpha A", chain: tieChain }),
        ]);

        const groups = await listAdminClubGroups();

        expect(groups.map((group) => group.chain?.name ?? "Unchained")).toEqual(
            ["Big Chain", "Alpha Chain", "Small Chain", "Unchained"],
        );
        expect(groups.map((group) => group.totals.clubCount)).toEqual([
            2, 1, 1, 1,
        ]);
    });
});
