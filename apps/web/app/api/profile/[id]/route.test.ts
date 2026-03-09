import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/profile/updateUserProfileData", () => ({
    updateUserProfileData: vi.fn(),
}));

import { PUT } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockUpdateProfile = vi.mocked(updateUserProfileData);

const USER_ID = "user-abc";

function makeRequest(
    body: unknown = { zipCode: "10001" },
): [NextRequest, { params: Promise<{ id: string }> }] {
    const req = new NextRequest(`http://localhost/api/profile/${USER_ID}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    return [req, { params: Promise.resolve({ id: USER_ID }) }];
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("PUT /api/profile/[id]", () => {
    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const [req, ctx] = makeRequest();
        const res = await PUT(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const [req, ctx] = makeRequest();
        const res = await PUT(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 200 with updated profile on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: USER_ID,
        });
        const updatedProfile = {
            id: "profile-1",
            zipCode: "10001",
            emailOptin: false,
        };
        mockUpdateProfile.mockResolvedValue(updatedProfile as any);

        const [req, ctx] = makeRequest();
        const res = await PUT(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.response).toEqual(updatedProfile);
    });
});
