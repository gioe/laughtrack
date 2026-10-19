import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({ auth: vi.fn(), get: vi.fn() }));
vi.mock("@/lib/auth/requireAdmin", () => ({ requireAdminForApi: mocks.auth }));
vi.mock("@/lib/db", () => ({ db: {} }));
vi.mock("@/lib/admin/curation/inbox", () => ({
    createInbox: () => ({ get: mocks.get }),
}));
import { GET } from "./route";
beforeEach(() => {
    vi.resetAllMocks();
    mocks.auth.mockResolvedValue({ ok: true, context: { profileId: "admin" } });
    mocks.get.mockResolvedValue({ items: [], hasMore: false });
});
it.each([401, 422, 403])(
    "protects queue, detail and endpoint search (%s)",
    async (status) => {
        mocks.auth.mockResolvedValue({
            ok: false,
            response: NextResponse.json({ error: "Denied" }, { status }),
        });
        for (const suffix of ["", "?id=x", "?lookup=comedian"])
            expect(
                (
                    await GET(
                        new NextRequest(
                            "http://localhost/api/admin/curation/inbox" +
                                suffix,
                        ),
                    )
                ).status,
            ).toBe(status);
        expect(mocks.get).not.toHaveBeenCalled();
    },
);
it("passes filters to the read service", async () => {
    expect(
        (
            await GET(
                new NextRequest(
                    "http://localhost/api/admin/curation/inbox?view=intake&state=blocked&q=Special",
                ),
            )
        ).status,
    ).toBe(200);
    expect(mocks.get).toHaveBeenCalledWith({
        view: "intake",
        state: "blocked",
        q: "Special",
    });
});
it("reports unavailable migrations without returning database internals", async () => {
    mocks.get.mockRejectedValue(new Error("secret DSN"));
    const response = await GET(
        new NextRequest("http://localhost/api/admin/curation/inbox"),
    );
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain("secret");
});
