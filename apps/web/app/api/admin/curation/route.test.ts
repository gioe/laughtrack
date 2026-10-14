import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    submit: vi.fn(),
    preview: vi.fn(),
    getRequest: vi.fn(),
}));
vi.mock("@/lib/auth/requireAdmin", () => ({ requireAdminForApi: mocks.auth }));
vi.mock("@/lib/admin/curation/runtime", () => ({ curation: mocks }));
import { GET, POST } from "./route";
import { CurationError } from "@/lib/admin/curation/decisions";
const command = {
    requestId: "6e1b1252-05b6-4aa9-a416-93f7593c6fa6",
    target: { type: "entity", id: "a", kind: "comedian", scope: "entity" },
    action: "block",
    expectedVersion: 0,
    reason: "Invalid performer",
};
const request = (body: unknown) =>
    new NextRequest("http://localhost/api/admin/curation", {
        method: "POST",
        body: JSON.stringify(body),
    });
beforeEach(() => {
    vi.resetAllMocks();
    mocks.auth.mockResolvedValue({
        ok: true,
        context: { profileId: "admin", userId: "u" },
    });
    mocks.submit.mockResolvedValue({ status: "applied" });
});
it.each([401, 422, 403])(
    "requires admin authorization for all operations (%s)",
    async (status) => {
        mocks.auth.mockResolvedValue({
            ok: false,
            response: NextResponse.json({ error: "Denied" }, { status }),
        });
        expect(
            (await GET(new NextRequest("http://localhost/api/admin/curation")))
                .status,
        ).toBe(status);
        expect(
            (await POST(request({ operation: "submit", command }))).status,
        ).toBe(status);
        expect(
            (await POST(request({ operation: "preview", command }))).status,
        ).toBe(status);
        expect(mocks.submit).not.toHaveBeenCalled();
        expect(mocks.preview).not.toHaveBeenCalled();
        expect(mocks.getRequest).not.toHaveBeenCalled();
    },
);
it("uses authenticated attribution and rejects spoofing/malformed scope", async () => {
    expect((await POST(request({ operation: "submit", command }))).status).toBe(
        200,
    );
    expect(mocks.submit).toHaveBeenCalledWith(command, "admin");
    expect(
        (
            await POST(
                request({
                    operation: "submit",
                    command: { ...command, actor: "forged" },
                }),
            )
        ).status,
    ).toBe(400);
    expect(
        (
            await POST(
                request({
                    operation: "submit",
                    command: {
                        ...command,
                        target: { ...command.target, scope: undefined },
                    },
                }),
            )
        ).status,
    ).toBe(400);
});
it.each([
    ["pending", 202],
    ["applied", 200],
    ["conflict", 409],
    ["failed", 500],
])("returns accurate processing status %s", async (status, code) => {
    mocks.submit.mockResolvedValue({ status });
    expect((await POST(request({ operation: "submit", command }))).status).toBe(
        code,
    );
});
it("previews without submitting and returns disabled workflow conflicts", async () => {
    mocks.preview.mockResolvedValue({ available: false });
    expect(
        (await POST(request({ operation: "preview", command }))).status,
    ).toBe(200);
    expect(mocks.submit).not.toHaveBeenCalled();
    mocks.submit.mockRejectedValue(
        new CurationError("adapter_unavailable", "Not enabled", 503),
    );
    expect((await POST(request({ operation: "submit", command }))).status).toBe(
        503,
    );
});
it("exposes actionable stale state and request receipts", async () => {
    mocks.submit.mockRejectedValue(
        new CurationError("stale_version", "Refresh", 409, {
            id: "a",
            kind: "comedian",
            version: 2,
            disposition: "blocked",
        }),
    );
    const response = await POST(request({ operation: "submit", command }));
    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({
        code: "stale_version",
        current: { version: 2 },
    });
    mocks.getRequest.mockResolvedValue({ status: "pending" });
    expect(
        (
            await GET(
                new NextRequest(
                    `http://localhost/api/admin/curation?requestId=${command.requestId}`,
                ),
            )
        ).status,
    ).toBe(200);
    expect(
        (
            await GET(
                new NextRequest(
                    "http://localhost/api/admin/curation?requestId=bad",
                ),
            )
        ).status,
    ).toBe(400);
});
