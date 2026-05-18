import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    findFirstUserProfile: vi.fn(),
}));

vi.mock("@/auth", () => ({
    auth: mocks.auth,
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            findFirst: mocks.findFirstUserProfile,
        },
    },
}));

import { requireAdminForApi } from "./requireAdmin";

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe("requireAdminForApi", () => {
    it("rejects stale admin sessions whose database profile role was demoted", async () => {
        mocks.auth.mockResolvedValue(adminSession);
        mocks.findFirstUserProfile.mockResolvedValue({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        });

        const gate = await requireAdminForApi();

        expect(gate.ok).toBe(false);
        if (!gate.ok) {
            expect(gate.response.status).toBe(403);
        }
        expect(mocks.findFirstUserProfile).toHaveBeenCalledWith({
            where: {
                OR: [{ id: "profile-1" }, { userid: "user-1" }],
            },
            select: {
                id: true,
                userid: true,
                role: true,
            },
        });
    });

    it("returns admin context from the current database profile", async () => {
        mocks.auth.mockResolvedValue(adminSession);
        mocks.findFirstUserProfile.mockResolvedValue({
            id: "profile-1",
            userid: "user-1",
            role: "admin",
        });

        const gate = await requireAdminForApi();

        expect(gate).toEqual({
            ok: true,
            context: {
                userId: "user-1",
                profileId: "profile-1",
            },
        });
    });
});
