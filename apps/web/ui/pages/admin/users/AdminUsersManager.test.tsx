/**
 * @vitest-environment happy-dom
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { AdminUserListItem } from "@/lib/admin/users";
import AdminUsersManager from "./AdminUsersManager";

const users: AdminUserListItem[] = [
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
            ],
        },
    },
    {
        id: "user-2",
        name: "Regular User",
        email: "regular@example.com",
        emailVerifiedAt: null,
        image: null,
        createdAt: "2026-05-02T12:00:00.000Z",
        updatedAt: "2026-05-02T12:00:00.000Z",
        accountProviders: ["credentials"],
        accountCount: 1,
        refreshTokenCount: 0,
        sentNotificationCount: 0,
        profile: {
            id: "profile-2",
            role: "user",
            emailShowNotifications: false,
            pushShowNotifications: false,
            comedianOnboardingCompleted: false,
            zipCode: null,
            nearbyDistanceMiles: null,
            favoriteComedians: [],
        },
    },
    {
        id: "user-3",
        name: null,
        email: "missing-profile@example.com",
        emailVerifiedAt: null,
        image: null,
        createdAt: "2026-04-30T12:00:00.000Z",
        updatedAt: "2026-04-30T12:00:00.000Z",
        accountProviders: [],
        accountCount: 0,
        refreshTokenCount: 0,
        sentNotificationCount: 0,
        profile: null,
    },
];

afterEach(() => {
    cleanup();
});

describe("AdminUsersManager", () => {
    it("filters users by search text", () => {
        render(<AdminUsersManager users={users} />);

        fireEvent.change(screen.getByLabelText("Search users"), {
            target: { value: "funny person" },
        });

        expect(screen.getByText("Matt Gioe")).toBeTruthy();
        expect(screen.queryByText("Regular User")).toBeNull();
        expect(screen.queryByText("missing-profile@example.com")).toBeNull();
    });

    it("filters users by role", () => {
        render(<AdminUsersManager users={users} />);

        fireEvent.change(screen.getByLabelText("Role"), {
            target: { value: "missing-profile" },
        });

        expect(screen.getByText("missing-profile@example.com")).toBeTruthy();
        expect(screen.queryByText("Matt Gioe")).toBeNull();
        expect(screen.queryByText("Regular User")).toBeNull();
    });

    it("sorts users by email", () => {
        render(<AdminUsersManager users={users} />);

        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "email-asc" },
        });

        const headings = screen.getAllByRole("heading", { level: 3 });
        expect(headings[0].textContent).toBe("Matt Gioe");
        expect(headings[1].textContent).toBe("Unnamed user");
        expect(headings[2].textContent).toBe("Regular User");
    });

    it("paginates users", () => {
        render(<AdminUsersManager users={users} />);

        fireEvent.change(screen.getAllByLabelText("Per page")[0], {
            target: { value: "10" },
        });

        expect(screen.getAllByText("1-3 of 3 users")).toHaveLength(2);
    });
});
