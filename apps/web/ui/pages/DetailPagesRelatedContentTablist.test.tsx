/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ClubDetailTabs from "@/ui/pages/entity/club/detailTabs";
import ComedianDetailTabs from "@/ui/pages/entity/comedian/tabs";
import PodcastDetail from "@/ui/pages/entity/podcast";
import ShowDetailTabs from "@/ui/pages/entity/show/detailTabs";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

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

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: true,
    }),
}));

vi.mock("@/ui/pages/search/filterBar", () => ({
    default: () => <div data-testid="filter-bar" />,
}));

vi.mock("@/ui/pages/search/table", () => ({
    default: () => <div data-testid="show-table" />,
}));

vi.mock("@/ui/pages/entity/club/showRooms", () => ({
    default: () => <div data-testid="club-show-rooms" />,
}));

vi.mock("@/ui/pages/entity/club/siblings", () => ({
    default: () => <div data-testid="sibling-locations" />,
}));

vi.mock("@/ui/pages/entity/comedian/pastShows", () => ({
    default: () => <div data-testid="past-shows" />,
}));

vi.mock("@/ui/pages/entity/comedian/related", () => ({
    default: () => <div data-testid="related-comedians" />,
}));

vi.mock("@/ui/pages/entity/comedian/podcastAppearances", () => ({
    default: () => <div data-testid="podcast-appearances" />,
}));

vi.mock("@/ui/pages/entity/show/lineupSection", () => ({
    default: () => <div data-testid="show-lineup" />,
}));

vi.mock("@/ui/pages/entity/show/relatedShows", () => ({
    default: () => <div data-testid="related-shows" />,
}));

vi.mock("@/ui/components/grid/comedian", () => ({
    default: () => <div data-testid="comedian-grid" />,
}));

vi.mock("@/ui/components/cards/entity", () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="entity-card">{children}</div>
    ),
}));

const show = { id: 1, room: "Main Room" } as ShowDTO;
const comedian = { id: 2, name: "Jane Comic" } as ComedianDTO;
const podcast: PodcastDTO = {
    id: 3,
    slug: "good-podcast",
    title: "Good Podcast",
    authorName: "Jane Host",
    websiteUrl: "https://example.com",
    feedUrl: null,
    imageUrl: null,
    description: null,
    episodeCount: 0,
};

describe("detail page related-content tablists", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders the comedian detail related-content tablist", () => {
        render(
            <ComedianDetailTabs
                shows={[show]}
                total={1}
                filters={[]}
                comedianName="Jane Comic"
                relatedComedians={[comedian]}
                podcastAppearances={[]}
            />,
        );

        expect(
            screen.getByRole("tablist", { name: /comedian detail sections/i }),
        ).toBeTruthy();
        expect(screen.getByRole("tab", { name: /shows/i })).toBeTruthy();
        expect(screen.getByRole("tab", { name: /podcasts/i })).toBeTruthy();
    });

    it("renders the club detail tablist when shows and sibling locations are both present", () => {
        render(
            <ClubDetailTabs
                chainName="Laugh Factory"
                filters={[]}
                shows={[show]}
                siblings={[
                    {
                        name: "Laugh Factory Chicago",
                        city: "Chicago",
                        state: "IL",
                        imageUrl: "https://example.com/club.jpg",
                    },
                ]}
                total={1}
            />,
        );

        expect(
            screen.getByRole("tablist", { name: /club detail sections/i }),
        ).toBeTruthy();
        expect(screen.getByRole("tab", { name: /shows/i })).toBeTruthy();
        expect(screen.getByRole("tab", { name: /locations/i })).toBeTruthy();
    });

    it("renders the show detail tablist when lineup and related shows are both present", () => {
        render(
            <ShowDetailTabs
                clubName="The Club"
                lineup={[{ id: 2, name: "Jane Comic" }] as never}
                relatedShows={[show]}
            />,
        );

        expect(
            screen.getByRole("tablist", { name: /show detail sections/i }),
        ).toBeTruthy();
        expect(screen.getByRole("tab", { name: /lineup/i })).toBeTruthy();
        expect(screen.getByRole("tab", { name: /more shows/i })).toBeTruthy();
    });

    it("renders the podcast detail tablist when episodes and related comedians are both present", () => {
        render(
            <PodcastDetail
                podcast={podcast}
                episodes={[]}
                relatedComedians={[comedian]}
            />,
        );

        expect(
            screen.getByRole("tablist", { name: /podcast detail sections/i }),
        ).toBeTruthy();
        expect(screen.getByRole("tab", { name: /episodes/i })).toBeTruthy();
        expect(screen.getByRole("tab", { name: /comedians/i })).toBeTruthy();
    });
});
