/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import PodcastDetail from "@/ui/pages/entity/podcast";
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

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/hooks/useMotionProps", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/ui/components/grid/comedian", () => ({
    default: () => <div data-testid="comedian-grid" />,
}));

vi.mock("@/ui/components/cards/entity", () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="entity-card">{children}</div>
    ),
}));

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
};

const noEpisodes: PodcastEpisodeDTO[] = [];

describe("PodcastDetail primary CTA", () => {
    afterEach(() => {
        cleanup();
    });

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
