import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    propose: vi.fn(),
    preview: vi.fn(),
    submit: vi.fn(),
    history: vi.fn(),
}));
vi.mock("@/lib/auth/requireAdmin", () => ({ requireAdminForApi: mocks.auth }));
vi.mock("@/lib/admin/curation/runtime", () => ({ parentRelationships: mocks }));
import { GET, POST } from "./route";
import { CurationError } from "@/lib/admin/curation/decisions";
const request = (body: unknown) =>
    new NextRequest("http://localhost/api/admin/curation/parents", {
        method: "POST",
        body: JSON.stringify(body),
    });
beforeEach(() => {
    vi.resetAllMocks();
    mocks.auth.mockResolvedValue({ ok: true, context: { profileId: "admin" } });
    mocks.history.mockResolvedValue([]);
    mocks.submit.mockResolvedValue({ status: "applied" });
});
it.each([401, 422, 403])(
    "requires admin authorization for every operation (%s)",
    async (status) => {
        mocks.auth.mockResolvedValue({
            ok: false,
            response: NextResponse.json({ error: "Denied" }, { status }),
        });
        expect(
            (
                await GET(
                    new NextRequest(
                        "http://localhost/api/admin/curation/parents?childId=1",
                    ),
                )
            ).status,
        ).toBe(status);
        for (const operation of ["propose", "preview", "submit"])
            expect((await POST(request({ operation }))).status).toBe(status);
        for (const name of ["propose", "preview", "submit", "history"] as const)
            expect(mocks[name]).not.toHaveBeenCalled();
    },
);
it("previews without applying and attributes proposals and decisions to the authenticated admin", async () => {
    const input = { childId: 1, parentId: 2 };
    mocks.preview.mockResolvedValue({ effects: ["Confirm"] });
    mocks.propose.mockResolvedValue({ relationshipId: "edge" });
    expect(
        (await POST(request({ operation: "preview", ...input }))).status,
    ).toBe(200);
    expect(mocks.submit).not.toHaveBeenCalled();
    await POST(request({ operation: "propose", ...input }));
    expect(mocks.propose).toHaveBeenCalledWith(input, "admin");
    await POST(request({ operation: "submit", ...input }));
    expect(mocks.submit).toHaveBeenCalledWith(input, "admin");
});
it("returns history and actionable stale-preview errors", async () => {
    expect(
        (
            await GET(
                new NextRequest(
                    "http://localhost/api/admin/curation/parents?childId=1",
                ),
            )
        ).status,
    ).toBe(200);
    expect(mocks.history).toHaveBeenCalledWith(1);
    expect(
        (
            await GET(
                new NextRequest(
                    "http://localhost/api/admin/curation/parents?childId=bad",
                ),
            )
        ).status,
    ).toBe(400);
    mocks.submit.mockRejectedValue(
        new CurationError("stale_preview", "Preview again"),
    );
    const response = await POST(request({ operation: "submit" }));
    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({ code: "stale_preview" });
});
