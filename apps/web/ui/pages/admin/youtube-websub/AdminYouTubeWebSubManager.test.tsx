/**
 * @vitest-environment happy-dom
 */

import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
    YouTubeWebSubComedianRow,
    YouTubeWebSubEventRow,
    YouTubeWebSubSettingsView,
} from "@/lib/admin/youtubeWebSub";
import AdminYouTubeWebSubManager from "./AdminYouTubeWebSubManager";

const settings: YouTubeWebSubSettingsView = {
    feedIngestionEnabled: false,
    pushDeliveryEnabled: false,
};

const comedians: YouTubeWebSubComedianRow[] = [
    {
        uuid: "comedian-1",
        name: "Jane Comic",
        youtubeChannelId: "UC-1",
        youtubeLiveFeedEnabled: false,
        youtubeLiveNotificationsEnabled: false,
        subscriptionStatus: "subscribed",
        leaseExpiresAt: "2026-07-05T00:00:00.000Z",
        lastSubscribeError: null,
        recentEventStatus: "received",
        recentEventAt: "2026-06-29T00:00:00.000Z",
    },
];

const events: YouTubeWebSubEventRow[] = [
    {
        id: 42,
        comedianId: "comedian-1",
        comedianName: "Jane Comic",
        youtubeChannelId: "UC-1",
        youtubeVideoId: "vid-1",
        videoTitle: "Live tonight",
        eventStatus: "received",
        verificationStatus: "pending",
        suppressionReason: null,
        failureReason: null,
        receivedAt: "2026-06-29T00:00:00.000Z",
    },
];

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
});

describe("AdminYouTubeWebSubManager", () => {
    it("renders global toggles, comedian flags, and the event listing", () => {
        render(
            <AdminYouTubeWebSubManager
                settings={settings}
                comedians={comedians}
                events={events}
            />,
        );

        expect(
            (
                screen.getByLabelText(
                    "Feed ingestion enabled",
                ) as HTMLInputElement
            ).checked,
        ).toBe(false);
        expect(
            (
                screen.getByLabelText(
                    "Push delivery enabled",
                ) as HTMLInputElement
            ).checked,
        ).toBe(false);
        expect(
            screen.getByLabelText("Live feed for Jane Comic"),
        ).toBeTruthy();
        // event row content
        expect(screen.getByText("Live tonight")).toBeTruthy();
        expect(screen.getByText("vid-1")).toBeTruthy();
    });

    it("PATCHes the global setting when a toggle is flipped", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockResolvedValueOnce(
            new Response(
                JSON.stringify({
                    ok: true,
                    settings: {
                        feedIngestionEnabled: true,
                        pushDeliveryEnabled: false,
                    },
                }),
                { status: 200 },
            ),
        );

        render(
            <AdminYouTubeWebSubManager
                settings={settings}
                comedians={comedians}
                events={events}
            />,
        );

        fireEvent.click(screen.getByLabelText("Feed ingestion enabled"));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/admin/youtube-websub",
                expect.objectContaining({ method: "PATCH" }),
            );
        });
        const body = JSON.parse(
            (fetchMock.mock.calls[0][1]?.body as string) ?? "{}",
        );
        expect(body).toEqual({ feedIngestionEnabled: true });
        await waitFor(() => {
            expect(
                (
                    screen.getByLabelText(
                        "Feed ingestion enabled",
                    ) as HTMLInputElement
                ).checked,
            ).toBe(true);
        });
    });

    it("PATCHes the per-comedian flag to the comedian endpoint", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockResolvedValueOnce(
            new Response(JSON.stringify({ ok: true }), { status: 200 }),
        );

        render(
            <AdminYouTubeWebSubManager
                settings={settings}
                comedians={comedians}
                events={events}
            />,
        );

        fireEvent.click(screen.getByLabelText("Live feed for Jane Comic"));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/admin/youtube-websub/comedians/comedian-1",
                expect.objectContaining({ method: "PATCH" }),
            );
        });
    });

    it("loads and renders the raw payload, parsed IDs, verification, and suppression on view", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockResolvedValueOnce(
            new Response(
                JSON.stringify({
                    event: {
                        id: 42,
                        comedianId: "comedian-1",
                        comedianName: "Jane Comic",
                        youtubeChannelId: "UC-1",
                        youtubeVideoId: "vid-1",
                        videoTitle: "Live tonight",
                        videoUrl: "https://youtu.be/vid-1",
                        topicUrl: "https://topic",
                        eventStatus: "received",
                        verificationStatus: "verified-live",
                        liveBroadcastContent: "live",
                        scheduledStartTime: null,
                        actualStartTime: null,
                        publishedAt: null,
                        verifiedAt: null,
                        failureReason: null,
                        suppressionReason: "duplicate",
                        payloadXml: "<feed><entry>raw</entry></feed>",
                        payloadJson: {},
                        receivedAt: "2026-06-29T00:00:00.000Z",
                    },
                }),
                { status: 200 },
            ),
        );

        render(
            <AdminYouTubeWebSubManager
                settings={settings}
                comedians={comedians}
                events={events}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: "View payload" }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/admin/youtube-websub?eventId=42",
            );
        });

        const payload = await screen.findByTestId("event-payload-xml");
        expect(payload.textContent).toContain(
            "<feed><entry>raw</entry></feed>",
        );
        expect(screen.getByText("verified-live")).toBeTruthy();
        expect(screen.getByText("duplicate")).toBeTruthy();
        // parsed IDs appear in the detail panel
        expect(screen.getAllByText("UC-1").length).toBeGreaterThan(0);
    });
});
