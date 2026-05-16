/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import PodcastMiniPlayer from "./index";
import {
    startPodcastEpisode,
    usePodcastPlayer,
} from "@/hooks/usePodcastPlayer";

const EPISODE = {
    id: 42,
    podcastName: "Comedy Pod",
    episodeTitle: "Working It Out",
    episodeUrl: "https://example.com/working-it-out",
    audioUrl: "https://cdn.example.com/working-it-out.mp3",
};

describe("PodcastMiniPlayer", () => {
    beforeEach(() => {
        usePodcastPlayer.getState().reset();
        vi.spyOn(window.HTMLMediaElement.prototype, "play").mockResolvedValue(
            undefined,
        );
        vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(
            () => undefined,
        );
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        usePodcastPlayer.getState().reset();
    });

    it("stays mounted across child route changes while preserving the selected episode", async () => {
        const { rerender, getByRole, getByText } = render(
            <>
                <PodcastMiniPlayer />
                <main>First route</main>
            </>,
        );

        startPodcastEpisode(EPISODE);

        await waitFor(() => {
            expect(
                getByRole("button", { name: /pause Working It Out/i }),
            ).not.toBeNull();
        });
        expect(getByText("Working It Out")).not.toBeNull();

        rerender(
            <>
                <PodcastMiniPlayer />
                <main>Second route</main>
            </>,
        );

        expect(getByText("Working It Out")).not.toBeNull();
        expect(
            getByRole("button", { name: /pause Working It Out/i }),
        ).not.toBeNull();
    });

    it("uses one audio element when starting and pausing episodes", async () => {
        const { getByRole, container } = render(<PodcastMiniPlayer />);

        startPodcastEpisode(EPISODE);

        await waitFor(() => {
            expect(container.querySelectorAll("audio")).toHaveLength(1);
        });
        expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);

        fireEvent.click(getByRole("button", { name: /pause Working It Out/i }));

        expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalledTimes(1);
        expect(container.querySelectorAll("audio")).toHaveLength(1);

        fireEvent.click(getByRole("button", { name: /play Working It Out/i }));

        await waitFor(() => {
            expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(
                2,
            );
        });
        expect(container.querySelectorAll("audio")).toHaveLength(1);
    });

    it("shows the episode page fallback when audio loading fails", async () => {
        const { container, getByRole, getByText } = render(
            <PodcastMiniPlayer />,
        );

        startPodcastEpisode(EPISODE);
        const audio = await waitFor(() => {
            const element = container.querySelector("audio");
            expect(element).not.toBeNull();
            return element as HTMLAudioElement;
        });

        fireEvent.error(audio);

        expect(getByText(/audio unavailable/i)).not.toBeNull();
        const fallback = getByRole("link", {
            name: /open episode page for Working It Out/i,
        });
        expect(fallback.getAttribute("href")).toBe(
            "https://example.com/working-it-out",
        );
        expect(fallback.getAttribute("target")).toBe("_blank");
    });
});
