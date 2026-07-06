/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import NotificationCenterTab from "./NotificationCenterTab";

vi.mock("next/link", () => ({
    default: ({
        href,
        children,
    }: {
        href: string;
        children: React.ReactNode;
    }) => <a href={href}>{children}</a>,
}));

type FetchResponse = {
    ok: boolean;
    status: number;
    json: () => Promise<unknown>;
};
const jsonResponse = (body: unknown): FetchResponse => ({
    ok: true,
    status: 200,
    json: async () => body,
});

const sampleItem = {
    id: "legacy:comedian-1:555",
    title: "Taylor Tomlinson is performing near you",
    body: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
    comedianId: "comedian-1",
    comedianName: "Taylor Tomlinson",
    comedianImageUrl: "",
    comedians: [
        {
            comedianId: "comedian-1",
            comedianName: "Taylor Tomlinson",
            comedianImageUrl: "",
        },
    ],
    shows: [
        {
            showId: 555,
            subtitle: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
            showPageUrl: "https://laugh-track.com/show/555",
            showDate: "2026-07-01T02:00:00.000Z",
            clubName: "The Comedy Store",
            city: "Los Angeles",
            state: "CA",
        },
    ],
    route: null,
    channels: ["push", "email"],
    sentAt: new Date(Date.now() - 3600_000).toISOString(),
    isUnread: true,
};

const groupedItem = {
    id: "run-1",
    title: "2 comedians you follow have shows near you",
    body: "The Comedy Store, The Stand",
    comedianId: "comedian-1",
    comedianName: "Taylor Tomlinson",
    comedianImageUrl: "",
    comedians: [],
    shows: [{ showId: 555 }, { showId: 777 }],
    route: "favorites",
    channels: ["push"],
    sentAt: new Date(Date.now() - 3600_000).toISOString(),
    isUnread: true,
};

describe("NotificationCenterTab", () => {
    let fetchMock: ReturnType<typeof vi.fn>;
    let seenCalls: number;

    beforeEach(() => {
        seenCalls = 0;
        fetchMock = vi
            .fn()
            .mockImplementation((url: string, opts?: RequestInit) => {
                if (url === "/api/v1/me/notifications/seen") {
                    seenCalls += 1;
                    expect(opts?.method).toBe("POST");
                    return Promise.resolve(
                        jsonResponse({ data: { lastSeenAt: null } }),
                    );
                }
                if (url === "/api/v1/me/notifications") {
                    return Promise.resolve(
                        jsonResponse({
                            data: {
                                items: [sampleItem],
                                unreadCount: 1,
                                lastSeenAt: null,
                            },
                        }),
                    );
                }
                return Promise.resolve(jsonResponse({ data: {} }));
            });
        vi.stubGlobal("fetch", fetchMock);
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
    });

    it("lists notification history with a row linking to the show detail page", async () => {
        render(<NotificationCenterTab />);

        await waitFor(() => {
            expect(
                screen.getByText("Taylor Tomlinson is performing near you"),
            ).toBeTruthy();
        });

        const link = screen
            .getByText("Taylor Tomlinson is performing near you")
            .closest("a");
        expect(link?.getAttribute("href")).toBe("/show/555");
    });

    it("links a grouped entry to the Favorites tab", async () => {
        fetchMock.mockImplementation((url: string) => {
            if (url === "/api/v1/me/notifications/seen") {
                return Promise.resolve(
                    jsonResponse({ data: { lastSeenAt: null } }),
                );
            }
            if (url === "/api/v1/me/notifications") {
                return Promise.resolve(
                    jsonResponse({
                        data: {
                            items: [groupedItem],
                            unreadCount: 1,
                            lastSeenAt: null,
                        },
                    }),
                );
            }
            return Promise.resolve(jsonResponse({ data: {} }));
        });

        render(<NotificationCenterTab />);

        await waitFor(() => {
            expect(
                screen.getByText("2 comedians you follow have shows near you"),
            ).toBeTruthy();
        });

        const link = screen
            .getByText("2 comedians you follow have shows near you")
            .closest("a");
        expect(link?.getAttribute("href")).toBe("?tab=favorites&shows=555,777");
    });

    it("marks notifications seen on view and notifies the parent to clear the badge", async () => {
        const onSeen = vi.fn();
        render(<NotificationCenterTab onSeen={onSeen} />);

        await waitFor(() => {
            expect(seenCalls).toBe(1);
            expect(onSeen).toHaveBeenCalledTimes(1);
        });
    });

    it("renders an empty state when there is no history", async () => {
        fetchMock.mockImplementation((url: string) => {
            if (url === "/api/v1/me/notifications") {
                return Promise.resolve(
                    jsonResponse({
                        data: { items: [], unreadCount: 0, lastSeenAt: null },
                    }),
                );
            }
            return Promise.resolve(
                jsonResponse({ data: { lastSeenAt: null } }),
            );
        });

        render(<NotificationCenterTab />);

        await waitFor(() => {
            expect(screen.getByText("No notifications yet")).toBeTruthy();
        });
    });

    it("shows an error message when the feed fails to load", async () => {
        fetchMock.mockImplementation((url: string) => {
            if (url === "/api/v1/me/notifications") {
                return Promise.resolve({
                    ok: false,
                    status: 500,
                    json: async () => ({}),
                });
            }
            return Promise.resolve(
                jsonResponse({ data: { lastSeenAt: null } }),
            );
        });

        render(<NotificationCenterTab />);

        await waitFor(() => {
            expect(
                screen.getByText(/couldn't load your notifications/i),
            ).toBeTruthy();
        });
    });
});
