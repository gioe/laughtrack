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
import type { YouTubeWebSubSettingsView } from "@/lib/admin/youtubeWebSub";
import AdminFeatureFlagsManager from "./AdminFeatureFlagsManager";

const settings: YouTubeWebSubSettingsView = {
    feedIngestionEnabled: false,
    pushDeliveryEnabled: false,
};

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
});

describe("AdminFeatureFlagsManager", () => {
    it("renders the global YouTube WebSub flags", () => {
        render(<AdminFeatureFlagsManager settings={settings} />);

        expect(
            (
                screen.getByLabelText(
                    "Feed ingestion enabled",
                ) as HTMLInputElement
            ).checked,
        ).toBe(false);
        expect(
            (screen.getByLabelText("Push delivery enabled") as HTMLInputElement)
                .checked,
        ).toBe(false);
    });

    it("PATCHes the setting when a flag is flipped", async () => {
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

        render(<AdminFeatureFlagsManager settings={settings} />);

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
    });
});
