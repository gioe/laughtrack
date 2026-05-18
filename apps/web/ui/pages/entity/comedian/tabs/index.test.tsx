/**
 * @vitest-environment happy-dom
 */
import React, { useEffect } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";
import ComedianDetailTabs from "./index";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";

let pastMountCount = 0;
let podcastMountCount = 0;

vi.mock("@/ui/pages/search/table", () => ({
    default: () => <div data-testid="upcoming-shows">Upcoming shows</div>,
}));

vi.mock("@/ui/pages/search/filterBar", () => ({
    default: () => <div data-testid="filter-bar">Filters</div>,
}));

vi.mock("@/ui/pages/entity/comedian/pastShows", () => ({
    default: function MockPastShowsSection() {
        useEffect(() => {
            pastMountCount += 1;
        }, []);

        return <div data-testid="past-shows">Past show markup</div>;
    },
}));

vi.mock("@/ui/pages/entity/comedian/related", () => ({
    default: () => <div data-testid="related-comedians">Related comedians</div>,
}));

vi.mock("@/ui/pages/entity/comedian/podcastAppearances", () => ({
    default: function MockPodcastAppearancesSection({
        appearances,
    }: {
        appearances: ComedianPodcastAppearanceDTO[];
    }) {
        useEffect(() => {
            podcastMountCount += 1;
        }, []);

        return (
            <div data-testid="podcast-appearances">
                Podcast appearances: {appearances.length}
            </div>
        );
    },
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

const renderTabs = (podcastAppearances: ComedianPodcastAppearanceDTO[] = []) =>
    render(
        <ComedianDetailTabs
            shows={[{ id: 1 } as ShowDTO]}
            total={1}
            filters={[]}
            comedianName="Jane Comic"
            relatedComedians={[{ id: 2 } as ComedianDTO]}
            podcastAppearances={podcastAppearances}
        />,
    );

describe("ComedianDetailTabs", () => {
    beforeEach(() => {
        pastMountCount = 0;
        podcastMountCount = 0;
    });

    afterEach(() => {
        cleanup();
    });

    it("renders show markup on first paint without podcast markup", () => {
        const { container } = renderTabs();

        expect(
            container.querySelector('[data-testid="upcoming-shows"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="filter-bar"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="past-shows"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="related-comedians"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="podcast-appearances"]'),
        ).toBeNull();
    });

    it("keeps the shows tab mounted while switching tabs", () => {
        const { getByRole, container } = renderTabs([makeAppearance()]);

        expect(
            container.querySelector('[data-testid="past-shows"]'),
        ).not.toBeNull();
        expect(pastMountCount).toBe(1);

        fireEvent.click(getByRole("tab", { name: /podcasts/i }));
        fireEvent.click(getByRole("tab", { name: /shows/i }));

        expect(pastMountCount).toBe(1);
    });

    it("keeps the podcasts tab mounted after first activation", () => {
        const { getByRole, container } = renderTabs([
            makeAppearance({ id: 1 }),
            makeAppearance({ id: 2, appearanceRole: "host" }),
        ]);

        fireEvent.click(getByRole("tab", { name: /podcasts/i }));
        expect(
            container.querySelector('[data-testid="podcast-appearances"]'),
        ).not.toBeNull();
        expect(container.textContent).toContain("Podcast appearances: 2");
        expect(podcastMountCount).toBe(1);

        fireEvent.click(getByRole("tab", { name: /shows/i }));
        fireEvent.click(getByRole("tab", { name: /podcasts/i }));

        expect(podcastMountCount).toBe(1);
    });
});
