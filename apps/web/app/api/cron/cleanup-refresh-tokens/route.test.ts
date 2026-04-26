import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/refreshTokens", () => ({
    cleanupExpiredRefreshTokens: vi.fn(),
}));

import { POST } from "./route";
import { cleanupExpiredRefreshTokens } from "@/lib/auth/refreshTokens";

const mockCleanup = vi.mocked(cleanupExpiredRefreshTokens);

function makeRequest(headers: Record<string, string> = {}): NextRequest {
    return new NextRequest("http://localhost/api/cron/cleanup-refresh-tokens", {
        method: "POST",
        headers,
    });
}

const ORIGINAL_SECRET = process.env.CRON_SECRET;

beforeEach(() => {
    vi.clearAllMocks();
    process.env.CRON_SECRET = "test-secret-value";
});

afterEach(() => {
    if (ORIGINAL_SECRET === undefined) delete process.env.CRON_SECRET;
    else process.env.CRON_SECRET = ORIGINAL_SECRET;
});

describe("POST /api/cron/cleanup-refresh-tokens", () => {
    it("returns 401 when no Authorization header is provided", async () => {
        const res = await POST(makeRequest());
        expect(res.status).toBe(401);
        expect(mockCleanup).not.toHaveBeenCalled();
    });

    it("returns 401 when the Bearer token does not match", async () => {
        const res = await POST(
            makeRequest({ authorization: "Bearer wrong-value-here" }),
        );
        expect(res.status).toBe(401);
        expect(mockCleanup).not.toHaveBeenCalled();
    });

    it("returns 401 when CRON_SECRET is unset", async () => {
        delete process.env.CRON_SECRET;
        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );
        expect(res.status).toBe(401);
        expect(mockCleanup).not.toHaveBeenCalled();
    });

    it("returns the deleted count when the Bearer token matches", async () => {
        mockCleanup.mockResolvedValue({ deleted: 42 });

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ deleted: 42 });
        expect(mockCleanup).toHaveBeenCalledTimes(1);
    });

    it("returns 500 with cleanup_failed when the cleanup throws", async () => {
        const errorSpy = vi
            .spyOn(console, "error")
            .mockImplementation(() => {});
        mockCleanup.mockRejectedValue(new Error("db unavailable"));

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "cleanup_failed" });
        expect(mockCleanup).toHaveBeenCalledTimes(1);
        expect(errorSpy).toHaveBeenCalled();
        errorSpy.mockRestore();
    });
});
