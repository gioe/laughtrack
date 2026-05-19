import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    listAdminComedians: vi.fn(),
}));

vi.mock("@/lib/admin/comedianManagement", () => ({
    listAdminComedians: mocks.listAdminComedians,
}));

vi.mock("@/ui/pages/admin/comedians/AdminComedianManager", () => ({
    default: ({ comedians }: { comedians: Array<{ id: number }> }) => (
        <div data-testid="admin-comedian-manager">
            {comedians.length} comedians
        </div>
    ),
}));

import AdminComediansPage from "./page";

beforeEach(() => {
    vi.clearAllMocks();
    mocks.listAdminComedians.mockResolvedValue({
        comedians: [],
        denyListCount: 0,
    });
});

describe("AdminComediansPage", () => {
    it("renders counts and the manager", async () => {
        mocks.listAdminComedians.mockResolvedValue({
            comedians: [
                {
                    id: 1,
                    uuid: "uuid-1",
                    name: "Parent Comic",
                    popularity: 82,
                    totalShows: 9,
                    parent: null,
                    childCount: 1,
                    isBlocked: false,
                    blockReason: null,
                    blockAddedBy: null,
                    blockAddedAt: null,
                    latestTicketPurchase: null,
                    attributedPodcasts: [],
                },
                {
                    id: 2,
                    uuid: "uuid-2",
                    name: "Bad Match",
                    popularity: 1,
                    totalShows: 0,
                    parent: { id: 1, name: "Parent Comic" },
                    childCount: 0,
                    isBlocked: true,
                    blockReason: "Not a comedian",
                    blockAddedBy: "profile-1",
                    blockAddedAt: "2026-05-19T12:00:00.000Z",
                    latestTicketPurchase: null,
                    attributedPodcasts: [],
                },
            ],
            denyListCount: 8,
        });

        const element = await AdminComediansPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Comedians");
        expect(markup).toContain(
            "2 comedians · 1 blocked records · 8 deny-listed names · 1 child profiles",
        );
        expect(markup).toContain("admin-comedian-manager");
    });
});
