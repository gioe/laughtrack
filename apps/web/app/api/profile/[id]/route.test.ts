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

function makeRequestRaw(
    body: string,
): [NextRequest, { params: Promise<{ id: string }> }] {
    const req = new NextRequest(`http://localhost/api/profile/${USER_ID}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body,
    });
    return [req, { params: Promise.resolve({ id: USER_ID }) }];
}

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

    it("returns 400 when body is invalid JSON", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: USER_ID,
        });

        const [req, ctx] = makeRequestRaw("not-json{{{");
        const res = await PUT(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/invalid json/i);
    });

    it("returns 400 with 'At least one field' when body has neither zipCode nor emailOptin", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: USER_ID,
        });

        const [req, ctx] = makeRequest({});
        const res = await PUT(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/at least one field/i);
    });

    it("returns 400 when zipCode is not a 5-digit string", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: USER_ID,
        });

        const [req, ctx] = makeRequest({ zipCode: "1234" });
        const res = await PUT(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/5-digit/i);
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
