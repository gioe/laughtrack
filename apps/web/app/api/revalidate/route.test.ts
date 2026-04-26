import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

import { POST } from "./route";
import { auth } from "@/auth";
import { revalidateTag } from "next/cache";

const mockAuth = vi.mocked(auth);
const mockRevalidateTag = vi.mocked(revalidateTag);

function makeRequest(
    headers: Record<string, string> = {},
    body?: unknown,
): NextRequest {
    return new NextRequest("http://localhost/api/revalidate", {
        method: "POST",
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
    });
}

const ORIGINAL_SECRET = process.env.REVALIDATE_SECRET;

beforeEach(() => {
    vi.clearAllMocks();
    process.env.REVALIDATE_SECRET = "test-secret-value";
    mockAuth.mockResolvedValue(null as never);
});

afterEach(() => {
    if (ORIGINAL_SECRET === undefined) delete process.env.REVALIDATE_SECRET;
    else process.env.REVALIDATE_SECRET = ORIGINAL_SECRET;
});

describe("POST /api/revalidate", () => {
    it("returns 401 when no Authorization header and no admin session", async () => {
        const res = await POST(makeRequest());
        expect(res.status).toBe(401);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });

    it("returns 401 when the Bearer token does not match", async () => {
        const res = await POST(
            makeRequest({ authorization: "Bearer wrong-value-here" }),
        );
        expect(res.status).toBe(401);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });

    it("returns 401 when REVALIDATE_SECRET is unset", async () => {
        delete process.env.REVALIDATE_SECRET;
        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );
        expect(res.status).toBe(401);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });

    it("revalidates all supported tags when the Bearer token matches", async () => {
        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.revalidated).toContain("home-page-data");
        expect(mockRevalidateTag).toHaveBeenCalled();
    });

    it("revalidates only the requested tags when a body is provided", async () => {
        const res = await POST(
            makeRequest(
                {
                    authorization: "Bearer test-secret-value",
                    "content-type": "application/json",
                },
                { tags: ["home-page-data"] },
            ),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ revalidated: ["home-page-data"] });
        expect(mockRevalidateTag).toHaveBeenCalledTimes(1);
        expect(mockRevalidateTag).toHaveBeenCalledWith("home-page-data");
    });

    it("returns 400 when an unknown tag is requested", async () => {
        const res = await POST(
            makeRequest(
                {
                    authorization: "Bearer test-secret-value",
                    "content-type": "application/json",
                },
                { tags: ["not-a-real-tag"] },
            ),
        );
        expect(res.status).toBe(400);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });

    it("returns 401 (not 500) when bearer and secret share string length but differ in byte length", async () => {
        // "café" is 4 JS code units but 5 UTF-8 bytes; "cafes" is 5 of each.
        // The pre-fix code compared string lengths (4 !== 5 → safe here),
        // but a request whose token has the same code-unit length as the
        // secret yet a different byte length would crash timingSafeEqual.
        // Construct that case: token "ée" (2 code units, 4 bytes) vs
        // secret "ab" (2 code units, 2 bytes).
        process.env.REVALIDATE_SECRET = "ab";
        const res = await POST(makeRequest({ authorization: "Bearer ée" }));
        expect(res.status).toBe(401);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });

    it("authorizes via admin session when no Bearer token is present", async () => {
        mockAuth.mockResolvedValue({
            profile: { role: "admin" },
        } as never);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.revalidated.length).toBeGreaterThan(0);
        expect(mockRevalidateTag).toHaveBeenCalled();
    });
});
