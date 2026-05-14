/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/react";
import PodcastAppearancesSection from "./index";
import type { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";

function makeAppearance(
    over: Partial<ComedianPodcastAppearanceDTO> = {},
): ComedianPodcastAppearanceDTO {
    return {
        id: 1,
        podcastName: "Good Podcast",
        episodeTitle: "A Good Episode",
        releaseDate: new Date("2026-04-02T00:00:00Z"),
        episodeUrl: "https://example.com/episode",
        ...over,
    };
}

describe("PodcastAppearancesSection", () => {
    afterEach(() => cleanup());

    it("renders nothing when the comedian has no podcast appearances", () => {
        const { container } = render(
            <PodcastAppearancesSection appearances={[]} />,
        );

        expect(container.firstChild).toBeNull();
    });

    it("renders one outbound row per podcast appearance", () => {
        const appearances = [
            makeAppearance({
                id: 10,
                podcastName: "Comedy Pod",
                episodeTitle: "Working It Out",
                releaseDate: new Date("2026-04-02T00:00:00Z"),
                episodeUrl: "https://example.com/working-it-out",
            }),
            makeAppearance({
                id: 11,
                podcastName: "Interview Pod",
                episodeTitle: "Long Form Talk",
                releaseDate: new Date("2026-03-01T00:00:00Z"),
                episodeUrl: "https://example.com/long-form-talk",
            }),
        ];

        const { getByRole, getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(
            getByRole("heading", { name: "Recent podcast appearances" }),
        ).not.toBeNull();
        expect(getByText("Working It Out")).not.toBeNull();
        expect(getByText(/Comedy Pod · Apr 2, 2026/)).not.toBeNull();
        expect(getByText("Long Form Talk")).not.toBeNull();

        const link = getByRole("link", { name: /Working It Out/i });
        expect(link.getAttribute("href")).toBe(
            "https://example.com/working-it-out",
        );
        expect(link.getAttribute("target")).toBe("_blank");
        expect(link.getAttribute("rel")).toBe("noopener noreferrer");
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
            container.querySelectorAll("a span span:first-child"),
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

        expect(getByText(/Good Podcast · May 3, 2026/)).not.toBeNull();
    });

    it("keeps undated appearances visible with a fallback label", () => {
        const appearances = [makeAppearance({ releaseDate: null })];

        const { getByText } = render(
            <PodcastAppearancesSection appearances={appearances} />,
        );

        expect(
            getByText(/Good Podcast · Release date unavailable/),
        ).not.toBeNull();
    });
});
