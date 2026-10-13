import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    list: vi.fn(),
    decide: vi.fn(),
}));
vi.mock("@/lib/auth/requireAdmin", () => ({ requireAdminForApi: mocks.auth }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("@/lib/admin/reviews", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/lib/admin/reviews")>()),
    listReviews: mocks.list,
    decideReview: mocks.decide,
}));
vi.mock("@/lib/db", () => ({ db: {} }));
import { GET, POST } from "./route";
beforeEach(() => {
    vi.clearAllMocks();
    mocks.auth.mockResolvedValue({
        ok: true,
        context: { profileId: "admin", userId: "user" },
    });
    mocks.list.mockResolvedValue({ items: [], total: 0, page: 1 });
});
it.each([401, 422, 403])(
    "rejects unauthorized review access (%i)",
    async (status) => {
        mocks.auth.mockResolvedValue({
            ok: false,
            response: NextResponse.json({ error: "Forbidden" }, { status }),
        });
        expect(
            (await GET(new NextRequest("http://localhost/api/admin/reviews")))
                .status,
        ).toBe(status);
        expect(
            (
                await POST(
                    new NextRequest("http://localhost/api/admin/reviews", {
                        method: "POST",
                    }),
                )
            ).status,
        ).toBe(status);
        expect(mocks.list).not.toHaveBeenCalled();
        expect(mocks.decide).not.toHaveBeenCalled();
    },
);
it("rejects malformed decisions before calling the service", async () => {
    expect(
        (
            await POST(
                new NextRequest("http://localhost/api/admin/reviews", {
                    method: "POST",
                    body: "{}",
                }),
            )
        ).status,
    ).toBe(400);
    expect(mocks.decide).not.toHaveBeenCalled();
});
it("uses the authenticated actor for valid decisions", async () => {
    mocks.decide.mockResolvedValue({ decisionId: "test" });
    const body = {
        workflow: "comedian_identity",
        id: "candidate",
        token: "a".repeat(64),
        action: "reject",
        reason: "A production title",
    };
    expect(
        (
            await POST(
                new NextRequest("http://localhost/api/admin/reviews", {
                    method: "POST",
                    body: JSON.stringify(body),
                }),
            )
        ).status,
    ).toBe(200);
    expect(mocks.decide).toHaveBeenCalledWith(
        expect.objectContaining(body),
        "admin",
    );
});
