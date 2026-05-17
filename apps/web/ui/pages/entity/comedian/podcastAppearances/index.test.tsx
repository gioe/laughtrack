/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import PodcastAppearancesSection from "./index";
import type { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import { usePodcastPlayer } from "@/hooks/usePodcastPlayer";

vi.mock("next/image", () => ({
    default: ({
        alt,
        src,
        className,
    }: {
        alt: string;
        src: string;
        className?: string;
    }) => <img alt={alt} src={src} className={className} />,
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

function makeAppearance(
    over: Partial<ComedianPodcastAppearanceDTO> = {},
): ComedianPodcastAppearanceDTO {
    return {
        id: 1,
        podcastName: "Good Podcast",
        podcastImageUrl: null,
        podcastAuthorName: null,
        podcastWebsiteUrl: null,
        episodeTitle: "A Good Episode",
        releaseDate: new Date("2026-04-02T00:00:00Z"),
        episodeUrl: "https://example.com/episode",
        audioUrl: "https://cdn.example.com/episode.mp3",
        durationSeconds: 3600,
        appearanceRole: "guest",
        ...over,
    };
}

describe("PodcastAppearancesSection", () => {
    afterEach(() => {
        cleanup();
        usePodcastPlayer.getState().reset();
    });

    it("renders nothing when the comedian has no podcast appearances", () => {
        const { container } = render(
            <PodcastAppearancesSection appearances={[]} />,
        );

        expect(container.firstChild).toBeNull();
    });

    it("renders nothing when the comedian has no playable podcast appearances", () => {
        const { container } = render(
            <PodcastAppearancesSection
                appearances={[
                    makeAppearance({
                        episodeTitle: "Link Only Episode",
                        audioUrl: null,
                    }),
                ]}
            />,
        );

        expect(container.firstChild).toBeNull();
    });

    it("renders one playable row per accepted podcast appearance", () => {
        const appearances = [
            makeAppearance({
                id: 10,
                podcastName: "Comedy Pod",
                episodeTitle: "Working It Out",
                releaseDate: new Date("2026-04-02T00:00:00Z"),
                episodeUrl: "https://example.com/working-it-out",
                audioUrl: "https://cdn.example.com/working-it-out.mp3",
                durationSeconds: 5420,
                appearanceRole: "guest",
            }),
            makeAppearance({
                id: 11,
                podcastName: "Interview Pod",
                episodeTitle: "Long Form Talk",
                releaseDate: new Date("2026-03-01T00:00:00Z"),
                episodeUrl: "https://example.com/long-form-talk",
                audioUrl: null,
            }),
        ];

        const { getByRole, getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(
            getByRole("heading", { name: "Recent podcast appearances" }),
        ).not.toBeNull();
        expect(getByText("Working It Out")).not.toBeNull();
        expect(getByText("Comedy Pod")).not.toBeNull();
        expect(getByText(/Apr 2, 2026/)).not.toBeNull();
        expect(getByText(/1 hr 30 min/)).not.toBeNull();
        expect(getByText(/Guest/)).not.toBeNull();
        expect(() => getByText("Long Form Talk")).toThrow();

        const link = getByRole("link", { name: /Working It Out/i });
        expect(link.getAttribute("href")).toBe(
            "https://example.com/working-it-out",
        );
        expect(link.getAttribute("target")).toBe("_blank");
        expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    });

    it("renders the appearance role as a separate badge", () => {
        const appearances = [
            makeAppearance({
                podcastName: "Hosted Pod",
                appearanceRole: "host",
            }),
        ];

        const { getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        const roleBadge = getByText("Host");
        expect(roleBadge.className).toContain("bg-copper/10");
        expect(roleBadge.className).toContain("text-copper");
        expect(getByText("Hosted Pod")).not.toBeNull();
        expect(getByText(/Apr 2, 2026 · 1 hr/)).not.toBeNull();
    });

    it("segments guest appearances from hosted podcast episodes", () => {
        const appearances = [
            makeAppearance({
                id: 10,
                podcastName: "Guest Pod",
                episodeTitle: "Guest Spot",
                appearanceRole: "guest",
            }),
            makeAppearance({
                id: 11,
                podcastName: "Hosted Pod",
                episodeTitle: "Host Chair",
                appearanceRole: "host",
            }),
            makeAppearance({
                id: 12,
                podcastName: "Cohosted Pod",
                episodeTitle: "Cohost Chair",
                appearanceRole: "cohost",
            }),
        ];

        const { getByRole, getByText, queryByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(
            getByRole("button", {
                name: /^podcast appearances$/i,
            }).getAttribute("aria-pressed"),
        ).toBe("true");
        expect(
            getByRole("button", {
                name: /comedian's podcasts/i,
            }).getAttribute("aria-pressed"),
        ).toBe("false");
        expect(getByText("Guest Spot")).not.toBeNull();
        expect(queryByText("Host Chair")).toBeNull();
        expect(queryByText("Cohost Chair")).toBeNull();

        fireEvent.click(getByRole("button", { name: /comedian's podcasts/i }));

        expect(
            getByRole("button", {
                name: /^podcast appearances$/i,
            }).getAttribute("aria-pressed"),
        ).toBe("false");
        expect(
            getByRole("button", {
                name: /comedian's podcasts/i,
            }).getAttribute("aria-pressed"),
        ).toBe("true");
        expect(queryByText("Guest Spot")).toBeNull();
        expect(getByText("Host Chair")).not.toBeNull();
        expect(getByText("Cohost Chair")).not.toBeNull();
    });

    it("renders rows in the order passed by the data layer", () => {
        const appearances = [
            makeAppearance({ id: 1, episodeTitle: "Most Recent" }),
            makeAppearance({ id: 2, episodeTitle: "Older" }),
        ];

        const { container } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        const titles = Array.from(
            container.querySelectorAll(
                '[data-testid="podcast-appearance-title"]',
            ),
        ).map((title) => title.textContent);
        expect(titles).toEqual(["Most Recent", "Older"]);
    });

    it("formats releaseDate when it arrived as an ISO string from unstable_cache", () => {
        const appearances = [
            {
                ...makeAppearance(),
                releaseDate: "2026-05-03T00:00:00Z",
            },
        ];

        const { getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(getByText("Good Podcast")).not.toBeNull();
        expect(getByText(/May 3, 2026/)).not.toBeNull();
    });

    it("keeps undated appearances visible with a fallback label", () => {
        const appearances = [makeAppearance({ releaseDate: null })];

        const { getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(getByText("Good Podcast")).not.toBeNull();
        expect(getByText(/Release date unavailable/)).not.toBeNull();
    });

    it("renders podcast artwork when an image URL is available", () => {
        const appearances = [
            makeAppearance({
                podcastName: "Artwork Pod",
                podcastImageUrl: "https://cdn.example.com/artwork.jpg",
            }),
        ];

        const { getByRole } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        const artwork = getByRole("img", { name: "Artwork Pod" });
        expect(artwork.getAttribute("src")).toBe(
            "https://cdn.example.com/artwork.jpg",
        );
        expect(artwork.className).toContain("object-cover");
    });

    it("uses EntityCard chrome and a muted podcast glyph when artwork is missing", () => {
        const appearances = [makeAppearance({ podcastImageUrl: null })];

        const { container, queryByRole } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(queryByRole("img", { name: "Good Podcast" })).toBeNull();
        const rowCard = container.querySelector("article");
        expect(rowCard?.className).toContain("rounded-xl");
        expect(rowCard?.className).toContain("shadow-md");
        expect(rowCard?.querySelector(".bg-muted svg")).not.toBeNull();
    });

    it("starts a playable podcast episode from the row without navigating away", () => {
        const appearances = [
            makeAppearance({
                episodeTitle: "Playable Episode",
                podcastName: "Playable Pod",
                episodeUrl: "https://example.com/playable",
                audioUrl: "https://cdn.example.com/playable.mp3",
            }),
        ];

        const { getByRole } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        fireEvent.click(
            getByRole("button", { name: /play Playable Episode/i }),
        );

        expect(usePodcastPlayer.getState().currentEpisode).toMatchObject({
            episodeTitle: "Playable Episode",
            podcastName: "Playable Pod",
            episodeUrl: "https://example.com/playable",
            audioUrl: "https://cdn.example.com/playable.mp3",
        });
        expect(usePodcastPlayer.getState().isPlaying).toBe(true);
    });

    it("marks the currently playing row and clears the indicator when playback stops", async () => {
        const appearances = [
            makeAppearance({ id: 101, episodeTitle: "First Episode" }),
            makeAppearance({ id: 102, episodeTitle: "Second Episode" }),
        ];

        const { getByRole, getByText, queryByLabelText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(queryByLabelText("Now playing")).toBeNull();

        fireEvent.click(getByRole("button", { name: /play First Episode/i }));

        expect(
            getByText("First Episode")
                .closest("li")
                ?.querySelector('[aria-label="Now playing"]'),
        ).not.toBeNull();
        expect(
            getByText("Second Episode")
                .closest("li")
                ?.querySelector('[aria-label="Now playing"]'),
        ).toBeNull();

        usePodcastPlayer.getState().pause();
        await waitFor(() => expect(queryByLabelText("Now playing")).toBeNull());

        fireEvent.click(getByRole("button", { name: /play Second Episode/i }));

        expect(
            getByText("First Episode")
                .closest("li")
                ?.querySelector('[aria-label="Now playing"]'),
        ).toBeNull();
        expect(
            getByText("Second Episode")
                .closest("li")
                ?.querySelector('[aria-label="Now playing"]'),
        ).not.toBeNull();

        usePodcastPlayer.getState().reset();
        await waitFor(() => expect(queryByLabelText("Now playing")).toBeNull());
    });

    it("keeps the episode page link as a fallback on playable rows", () => {
        const appearances = [
            makeAppearance({
                episodeTitle: "Playable Episode",
                episodeUrl: "https://example.com/playable",
                audioUrl: "https://cdn.example.com/playable.mp3",
            }),
        ];

        const { getByRole } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(
            getByRole("button", { name: /play Playable Episode/i }),
        ).not.toBeNull();
        const link = getByRole("link", { name: /Playable Episode/i });
        expect(link.getAttribute("href")).toBe("https://example.com/playable");
    });
});
