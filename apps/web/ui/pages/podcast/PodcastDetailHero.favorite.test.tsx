/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

const podcast: PodcastDTO = {
    id: 42,
    slug: "good-one",
    title: "Good One",
    authorName: "Vulture",
    websiteUrl: "https://example.com/good-one",
    feedUrl: "https://example.com/feed.xml",
    imageUrl: null,
    description: "Comedy interviews.",
    episodeCount: 0,
    isFavorite: false,
};

const episodes: PodcastEpisodeDTO[] = [];

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("PodcastDetail hero favorite button", () => {
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
                episodes={episodes}
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
