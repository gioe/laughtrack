import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    listAdminUsers: vi.fn(),
}));

vi.mock("@/lib/admin/users", () => ({
    listAdminUsers: mocks.listAdminUsers,
}));

import AdminUsersPage from "./page";
import type { AdminUsersData } from "@/lib/admin/users";

const usersData: AdminUsersData = {
    totals: {
        userCount: 2,
        profileCount: 1,
        adminCount: 1,
        favoriteComedianCount: 2,
        emailNotificationOptInCount: 1,
        pushNotificationOptInCount: 0,
    },
    users: [
        {
            id: "user-1",
            name: "Matt Gioe",
            email: "matt@example.com",
            emailVerifiedAt: "2026-05-18T12:00:00.000Z",
            image: "https://example.com/avatar.jpg",
            createdAt: "2026-05-01T12:00:00.000Z",
            updatedAt: "2026-05-18T12:00:00.000Z",
            accountProviders: ["google"],
            accountCount: 1,
            refreshTokenCount: 2,
            sentNotificationCount: 3,
            profile: {
                id: "profile-1",
                role: "admin",
                emailShowNotifications: true,
                pushShowNotifications: false,
                comedianOnboardingCompleted: true,
                zipCode: "10001",
                nearbyDistanceMiles: 25,
                favoriteComedians: [
                    {
                        id: 10,
                        uuid: "comic-1",
                        name: "Funny Person",
                        popularity: 91,
                        totalShows: 7,
                    },
                    {
                        id: 11,
                        uuid: "comic-2",
                        name: "Second Comic",
                        popularity: 42,
                        totalShows: 3,
                    },
                ],
            },
        },
        {
            id: "user-2",
            name: null,
            email: "no-profile@example.com",
            emailVerifiedAt: null,
            image: null,
            createdAt: "2026-05-02T12:00:00.000Z",
            updatedAt: "2026-05-02T12:00:00.000Z",
            accountProviders: [],
            accountCount: 0,
            refreshTokenCount: 0,
            sentNotificationCount: 0,
            profile: null,
        },
    ],
};

beforeEach(() => {
    vi.clearAllMocks();
    mocks.listAdminUsers.mockResolvedValue(usersData);
});

describe("AdminUsersPage", () => {
    it("renders user account details and favorites", async () => {
        const element = await AdminUsersPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Users");
        expect(markup).toContain("Account holders");
        expect(markup).toContain("Matt Gioe");
        expect(markup).toContain("matt@example.com");
        expect(markup).toContain("Funny Person");
        expect(markup).toContain("Second Comic");
        expect(markup).toContain("google");
        expect(markup).toContain("10001");
        expect(markup).toContain("no-profile@example.com");
        expect(markup).toContain("no profile");
    });

    it("renders an empty state", async () => {
        mocks.listAdminUsers.mockResolvedValue({
            totals: {
                userCount: 0,
                profileCount: 0,
                adminCount: 0,
                favoriteComedianCount: 0,
                emailNotificationOptInCount: 0,
                pushNotificationOptInCount: 0,
            },
            users: [],
        } satisfies AdminUsersData);

        const element = await AdminUsersPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("No user accounts found.");
    });
});
