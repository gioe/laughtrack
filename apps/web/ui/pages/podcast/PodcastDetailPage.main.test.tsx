/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
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

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: true,
    }),
}));

const podcast: PodcastDTO = {
    id: 1,
    slug: "the-good-podcast",
    title: "The Good Podcast",
    authorName: "Jane Host",
    websiteUrl: "https://example.com",
    feedUrl: "https://example.com/feed",
    imageUrl: null,
    description: "A delightful podcast.",
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
    },
];

describe("PodcastDetail page render", () => {
    afterEach(() => {
        cleanup();
    });

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
