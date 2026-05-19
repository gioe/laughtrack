import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    findFirstUserProfile: vi.fn(),
    notFound: vi.fn(() => {
        throw new Error("NEXT_NOT_FOUND");
    }),
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

vi.mock("next/navigation", () => ({
    notFound: mocks.notFound,
}));

import AdminLayout from "./layout";

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

async function renderAdminLayout() {
    const element = await AdminLayout({
        children: <section data-testid="admin-clubs-child">Club tools</section>,
    });

    return renderToStaticMarkup(element);
}

beforeEach(() => {
    vi.clearAllMocks();
    mocks.findFirstUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    });
});

describe("AdminLayout", () => {
    it("renders the branded admin shell for admin sessions", async () => {
        mocks.auth.mockResolvedValue(adminSession);

        const markup = await renderAdminLayout();

        expect(markup).toContain("LaughTrack Admin");
        expect(markup).toContain("Accounts and favorites");
        expect(markup).toContain("Club operations");
        expect(markup).toContain("Run status");
        expect(markup).toContain("Aliases and blocks");
        expect(markup).toContain('href="/admin/users"');
        expect(markup).toContain('href="/admin/clubs"');
        expect(markup).toContain('href="/admin/pipelines"');
        expect(markup).toContain('href="/admin/comedians"');
        expect(markup).toContain('data-testid="admin-clubs-child"');
        expect(mocks.notFound).not.toHaveBeenCalled();
    });

    it("rejects non-admin sessions by role", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", userid: "user-1", role: "user" },
        });
        mocks.findFirstUserProfile.mockResolvedValue({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        });

        await expect(renderAdminLayout()).rejects.toThrow("NEXT_NOT_FOUND");

        expect(mocks.notFound).toHaveBeenCalledOnce();
    });

    it("rejects stale admin sessions after the database profile was demoted", async () => {
        mocks.auth.mockResolvedValue(adminSession);
        mocks.findFirstUserProfile.mockResolvedValue({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        });

        await expect(renderAdminLayout()).rejects.toThrow("NEXT_NOT_FOUND");

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
        expect(mocks.notFound).toHaveBeenCalledOnce();
    });

    it("rejects anonymous sessions", async () => {
        mocks.auth.mockResolvedValue(null);

        await expect(renderAdminLayout()).rejects.toThrow("NEXT_NOT_FOUND");

        expect(mocks.notFound).toHaveBeenCalledOnce();
    });

    it("rejects authenticated sessions without a UserProfile", async () => {
        mocks.auth.mockResolvedValue({ user: { id: "user-1" } });

        await expect(renderAdminLayout()).rejects.toThrow("NEXT_NOT_FOUND");

        expect(mocks.notFound).toHaveBeenCalledOnce();
    });
});
