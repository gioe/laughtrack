import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    propose: vi.fn(),
    preview: vi.fn(),
    submit: vi.fn(),
    history: vi.fn(),
    previewReconciliation: vi.fn(),
    reconcile: vi.fn(),
}));
vi.mock("@/lib/auth/requireAdmin", () => ({ requireAdminForApi: mocks.auth }));
vi.mock("@/lib/admin/curation/runtime", () => ({ hostRelationships: mocks }));
import { GET, POST } from "./route";
import { CurationError } from "@/lib/admin/curation/decisions";
const request = (body: unknown) =>
    new NextRequest("http://localhost/api/admin/curation/hosts", {
        method: "POST",
        body: JSON.stringify(body),
    });
beforeEach(() => {
    vi.resetAllMocks();
    mocks.auth.mockResolvedValue({ ok: true, context: { profileId: "admin" } });
    for (const k of [
        "propose",
        "preview",
        "submit",
        "previewReconciliation",
        "reconcile",
    ] as const)
        mocks[k].mockResolvedValue({ status: "applied" });
    mocks.history.mockResolvedValue([]);
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
                        "http://localhost/api/admin/curation/hosts?podcastId=1",
                    ),
                )
            ).status,
        ).toBe(status);
        for (const operation of [
            "propose",
            "preview",
            "submit",
            "previewReconciliation",
            "reconcile",
        ])
            expect((await POST(request({ operation, input: {} }))).status).toBe(
                status,
            );
        expect(mocks.submit).not.toHaveBeenCalled();
        expect(mocks.reconcile).not.toHaveBeenCalled();
        expect(mocks.history).not.toHaveBeenCalled();
    },
);
it("attributes commands to the authenticated admin and previews without submitting", async () => {
    const input = { comedianId: 1, podcastId: 2 };
    await POST(request({ operation: "preview", input }));
    expect(mocks.submit).not.toHaveBeenCalled();
    for (const operation of ["propose", "submit", "reconcile"] as const) {
        expect((await POST(request({ operation, input }))).status).toBe(200);
        expect(mocks[operation]).toHaveBeenCalledWith(input, "admin");
    }
    expect(
        (await POST(request({ operation: "submit", input, actor: "forged" })))
            .status,
    ).toBe(400);
});
it("returns histories, version conflicts and explicit reconciliation previews", async () => {
    expect(
        (
            await GET(
                new NextRequest(
                    "http://localhost/api/admin/curation/hosts?podcastId=2",
                ),
            )
        ).status,
    ).toBe(200);
    expect(mocks.history).toHaveBeenCalledWith(2);
    await POST(
        request({ operation: "previewReconciliation", input: { id: "hold" } }),
    );
    expect(mocks.previewReconciliation).toHaveBeenCalledWith("hold");
    mocks.submit.mockRejectedValue(
        new CurationError("stale_version", "Refresh"),
    );
    expect(
        (await POST(request({ operation: "submit", input: {} }))).status,
    ).toBe(409);
});
