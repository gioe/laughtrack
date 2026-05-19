import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    listAdminClubGroups: vi.fn(),
}));

vi.mock("@/lib/admin/clubManagement", () => ({
    listAdminClubGroups: mocks.listAdminClubGroups,
}));

vi.mock("@/ui/pages/admin/clubs/AdminClubManager", () => ({
    default: ({ groups }: { groups: Array<{ key: string }> }) => (
        <div data-testid="admin-club-manager">{groups.length} groups</div>
    ),
}));

import AdminClubsPage from "./page";

beforeEach(() => {
    vi.clearAllMocks();
    mocks.listAdminClubGroups.mockResolvedValue([]);
});

describe("AdminClubsPage", () => {
    it("renders chain and club status counts", async () => {
        mocks.listAdminClubGroups.mockResolvedValue([
            {
                key: "chain-1",
                chain: {
                    id: 1,
                    name: "Funny Bone",
                    slug: "funny-bone",
                    website: "https://example.com/funny-bone",
                },
                clubs: [
                    {
                        id: 1,
                        name: "Funny Bone A",
                        visible: true,
                        status: "active",
                    },
                    {
                        id: 2,
                        name: "Funny Bone B",
                        visible: false,
                        status: "closed",
                    },
                ],
                totals: {
                    clubCount: 2,
                    visibleCount: 1,
                    activeCount: 1,
                    scrapedShowCount: 12,
                },
            },
        ]);

        const element = await AdminClubsPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Clubs");
        expect(markup).toContain("2 clubs · 1 chains · 1 hidden · 1 closed");
        expect(markup).toContain("admin-club-manager");
        expect(markup).not.toContain('href="/admin/deny-list"');
    });
});
