/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PodcastSearchCard from "./podcast";
import { useFavorite } from "@/hooks/useFavorite";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

vi.mock("next/link", () => ({
    default: ({
        children,
        href,
        className,
        ...props
    }: {
        children: React.ReactNode;
        href: string;
        className?: string;
    }) => (
        <a href={href} className={className} {...props}>
            {children}
        </a>
    ),
}));

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
    useFavorite: vi.fn(),
}));

const mockUseFavorite = vi.mocked(useFavorite);

const podcast: PodcastDTO = {
    id: 42,
    slug: "good-one",
    title: "Good One",
    authorName: "Vulture",
    websiteUrl: null,
    feedUrl: null,
    imageUrl: "https://cdn.example.com/good-one.jpg",
    description: null,
    episodeCount: 10,
    isFavorite: true,
};

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("PodcastSearchCard favorite toggle", () => {
    it("renders a favorite toggle wired to the podcast favorite mutation hook", () => {
        const handleFavoriteClick = vi.fn();
        mockUseFavorite.mockReturnValue({
            isFavorite: true,
            handleFavoriteClick,
            isAuthenticated: true,
        });

        render(<PodcastSearchCard podcast={podcast} />);

        expect(mockUseFavorite).toHaveBeenCalledWith({
            initialState: true,
            entityId: "42",
            entityType: "podcast",
        });

        const button = screen.getByRole("button", {
            name: "Remove Good One from favorites",
        });
        expect(button.getAttribute("aria-pressed")).toBe("true");

        fireEvent.click(button);
        expect(handleFavoriteClick).toHaveBeenCalledTimes(1);
    });
});
