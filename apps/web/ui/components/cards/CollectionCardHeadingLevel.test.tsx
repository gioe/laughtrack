/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClubSearchCard from "./club/search";
import ComedianGridCard from "./comedian";
import PodcastSearchCard from "./podcast";
import ShowCardHeader from "./show/header";
import { Show } from "@/objects/class/show/Show";
import type { ClubDTO } from "@/objects/class/club/club.interface";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { PodcastDTO } from "@/lib/data/podcast/interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";

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

vi.mock("framer-motion", () => ({
    motion: {
        div: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <div className={className}>{children}</div>,
        article: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <article className={className}>{children}</article>,
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: false,
    }),
}));

afterEach(() => {
    cleanup();
});

const club: ClubDTO = {
    id: 1,
    name: "Copper Room",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    address: "123 Main St",
    city: "New York",
    state: "NY",
    zipCode: "10001",
    showCount: 12,
};

const comedian: ComedianDTO = {
    id: 2,
    uuid: "comedian-2",
    name: "Jordan Temple",
    imageUrl: "",
    hasImage: false,
    socialData: {
        id: 20,
        instagramFollowers: null,
        tiktokFollowers: null,
        youtubeFollowers: null,
        instagramAccount: null,
        tiktokAccount: null,
        youtubeAccount: null,
        website: null,
        popularity: null,
        linktree: null,
    },
    showCount: 4,
};

const show: ShowDTO = {
    id: 3,
    clubId: 1,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
};

const podcast: PodcastDTO = {
    id: 4,
    slug: "copper-mic",
    title: "Copper Mic",
    authorName: "LaughTrack",
    websiteUrl: null,
    feedUrl: null,
    imageUrl: null,
    description: null,
    episodeCount: 10,
};

describe("collection card heading levels", () => {
    it("renders each collection card entity name as an h3", () => {
        render(
            <>
                <ClubSearchCard club={club} />
                <ComedianGridCard entity={comedian} />
                <ShowCardHeader show={new Show(show)} />
                <PodcastSearchCard podcast={podcast} />
            </>,
        );

        for (const name of [
            "Copper Room",
            "Jordan Temple",
            "Late Show",
            "Copper Mic",
        ]) {
            expect(
                screen.getByRole("heading", { level: 3, name }),
            ).toBeTruthy();
        }
    });
});
