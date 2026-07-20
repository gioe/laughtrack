import { afterEach, describe, expect, it, vi } from "vitest";
import { adminRequest } from "./adminRequest";

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("adminRequest", () => {
    it("returns a typed JSON success body and forwards the request unchanged", async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: vi.fn().mockResolvedValue({ saved: true }),
        });
        vi.stubGlobal("fetch", fetchMock);
        const init = {
            method: "POST",
            body: JSON.stringify({ name: "New value" }),
        };

        const body = await adminRequest<{ saved: boolean }>(
            "/api/admin/example",
            init,
        );

        expect(body.saved).toBe(true);
        expect(fetchMock).toHaveBeenCalledWith("/api/admin/example", init);
    });

    it("supports successful mutations without a JSON body", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({ ok: true, status: 204 }),
        );

        await expect(
            adminRequest("/api/admin/example"),
        ).resolves.toBeUndefined();
    });

    it("uses a structured API error and parses the response body once", async () => {
        const json = vi.fn().mockResolvedValue({ error: "Already exists" });
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({ ok: false, status: 409, json }),
        );

        await expect(
            adminRequest("/api/admin/example", undefined, {
                httpErrorMessage: "Save failed",
            }),
        ).rejects.toThrow("Already exists");
        expect(json).toHaveBeenCalledTimes(1);
    });

    it("uses the status fallback for a non-JSON HTTP failure", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: false,
                status: 502,
                json: vi
                    .fn()
                    .mockRejectedValue(new SyntaxError("Invalid JSON")),
            }),
        );

        await expect(adminRequest("/api/admin/example")).rejects.toThrow(
            "Request failed (502)",
        );
    });

    it("supports a caller-selected HTTP fallback", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: false,
                status: 500,
                json: vi.fn().mockResolvedValue({}),
            }),
        );

        await expect(
            adminRequest("/api/admin/example", undefined, {
                httpErrorMessage: "Save failed",
            }),
        ).rejects.toThrow("Save failed");
    });

    it("preserves Error messages from network failures", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockRejectedValue(new Error("Connection lost")),
        );

        await expect(adminRequest("/api/admin/example")).rejects.toThrow(
            "Connection lost",
        );
    });

    it("allows a string fallback to replace every network error", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockRejectedValue(new Error("Connection lost")),
        );

        await expect(
            adminRequest("/api/admin/example", undefined, {
                networkErrorMessage: "Save failed",
            }),
        ).rejects.toThrow("Save failed");
    });

    it("normalizes non-Error network failures and supports a callback fallback", async () => {
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue("offline"));

        await expect(adminRequest("/api/admin/example")).rejects.toThrow(
            "Network error",
        );
        await expect(
            adminRequest("/api/admin/example", undefined, {
                networkErrorMessage: (error) =>
                    error instanceof Error
                        ? error.message
                        : "Unknown network error",
            }),
        ).rejects.toThrow("Unknown network error");
    });
});
