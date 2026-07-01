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
import type { YouTubeWebSubEventRow } from "@/lib/admin/youtubeWebSub";
import AdminYouTubeWebSubManager from "./AdminYouTubeWebSubManager";

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
    it("renders the event listing without comedian feed rows or global feature toggles", () => {
        render(<AdminYouTubeWebSubManager events={events} />);

        expect(screen.queryByLabelText("Feed ingestion enabled")).toBeNull();
        expect(screen.queryByLabelText("Push delivery enabled")).toBeNull();
        expect(screen.queryByText("Comedian feeds")).toBeNull();
        // event row content
        expect(screen.getByText("Live tonight")).toBeTruthy();
        expect(screen.getByText("vid-1")).toBeTruthy();
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

        render(<AdminYouTubeWebSubManager events={events} />);

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
