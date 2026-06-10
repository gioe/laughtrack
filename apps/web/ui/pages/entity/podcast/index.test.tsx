/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PodcastDetail from "@/ui/pages/entity/podcast";
import { useFavorite } from "@/hooks/useFavorite";
import type {
    PodcastDTO,
    PodcastEpisodeDTO,
} from "@/lib/data/podcast/interface";

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

vi.mock("@/ui/components/grid/comedian", () => ({
    default: () => <div data-testid="comedian-grid" />,
}));

vi.mock("@/ui/components/cards/entity", () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="entity-card">{children}</div>
    ),
}));

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: vi.fn(),
}));

const mockUseFavorite = vi.mocked(useFavorite);

const basePodcast: PodcastDTO = {
    id: 1,
    slug: "the-good-podcast",
    title: "The Good Podcast",
    authorName: "Jane Host",
    websiteUrl: "https://example.com/the-good-podcast",
    feedUrl: "https://example.com/feed.xml",
    imageUrl: null,
    description: "A delightful podcast.",
    episodeCount: 0,
    hosts: [],
};

const noEpisodes: PodcastEpisodeDTO[] = [];

beforeEach(() => {
    mockUseFavorite.mockReturnValue({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: true,
    });
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("PodcastDetail hero favorite button", () => {
    const podcast: PodcastDTO = {
        ...basePodcast,
        id: 42,
        slug: "good-one",
        title: "Good One",
        authorName: "Vulture",
        websiteUrl: "https://example.com/good-one",
        description: "Comedy interviews.",
        isFavorite: false,
    };

    it("renders an Add to favorites button wired to the podcast favorite hook", () => {
        const handleFavoriteClick = vi.fn();
        mockUseFavorite.mockReturnValue({
            isFavorite: false,
            handleFavoriteClick,
            isAuthenticated: true,
        });

        render(
            <PodcastDetail
                podcast={podcast}
                episodes={noEpisodes}
                relatedComedians={[]}
            />,
        );

        expect(mockUseFavorite).toHaveBeenCalledWith({
            initialState: false,
            entityId: "42",
            entityType: "podcast",
        });

        const button = screen.getByRole("button", {
            name: "Add to favorites",
        });
        expect(button.getAttribute("aria-pressed")).toBe("false");

        fireEvent.click(button);
        expect(handleFavoriteClick).toHaveBeenCalledTimes(1);
    });
});

describe("PodcastDetail primary CTA", () => {
    it("renders a prominent button-level CTA linking to the podcast host site", () => {
        render(
            <PodcastDetail
                podcast={basePodcast}
                episodes={noEpisodes}
                relatedComedians={[]}
            />,
        );

        const cta = screen.getByRole("link", {
            name: /listen on host site/i,
        });
        expect(cta.getAttribute("href")).toBe(
            "https://example.com/the-good-podcast",
        );
        expect(cta.getAttribute("target")).toBe("_blank");
        expect(cta.getAttribute("rel")).toBe("noopener noreferrer");
        // Matches the roundedShimmer treatment used by the show Get Tickets CTA
        expect(cta.className).toContain("rounded-lg");
        expect(cta.className).toContain("bg-copper-dark");
    });

    it("renders a helper line describing that the CTA opens in a new tab", () => {
        const { container } = render(
            <PodcastDetail
                podcast={basePodcast}
                episodes={noEpisodes}
                relatedComedians={[]}
            />,
        );

        expect(container.textContent).toMatch(
            /opens the podcast's host site in a new tab/i,
        );
    });

    it("falls back to the RSS feed when the podcast has no website URL", () => {
        const podcast: PodcastDTO = { ...basePodcast, websiteUrl: null };

        render(
            <PodcastDetail
                podcast={podcast}
                episodes={noEpisodes}
                relatedComedians={[]}
            />,
        );

        const cta = screen.getByRole("link", { name: /open rss feed/i });
        expect(cta.getAttribute("href")).toBe("https://example.com/feed.xml");
        expect(cta.className).toContain("bg-copper-dark");
    });

    it("renders no primary CTA when neither website nor feed URL is set", () => {
        const podcast: PodcastDTO = {
            ...basePodcast,
            websiteUrl: null,
            feedUrl: null,
        };

        render(
            <PodcastDetail
                podcast={podcast}
                episodes={noEpisodes}
                relatedComedians={[]}
            />,
        );

        expect(
            screen.queryByRole("link", { name: /listen on host site/i }),
        ).toBeNull();
        expect(
            screen.queryByRole("link", { name: /open rss feed/i }),
        ).toBeNull();
    });
});

describe("PodcastDetail page render", () => {
    const podcast: PodcastDTO = {
        ...basePodcast,
        websiteUrl: "https://example.com",
        feedUrl: "https://example.com/feed",
        episodeCount: 2,
    };

    const episodes: PodcastEpisodeDTO[] = [
        {
            id: 10,
            title: "Episode One",
            description: "Pilot",
            releaseDate: new Date("2026-04-01T00:00:00Z"),
            durationSeconds: 1800,
            episodeUrl: "https://example.com/ep/1",
            audioUrl: "https://cdn.example.com/ep1.mp3",
            appearances: [],
        },
    ];

    it("contains exactly one <main> element when wrapped in the layout main", () => {
        const { container } = render(
            <main id="layout-main">
                <PodcastDetail
                    podcast={podcast}
                    episodes={episodes}
                    relatedComedians={[]}
                />
            </main>,
        );

        expect(container.querySelectorAll("main")).toHaveLength(1);
    });
});
