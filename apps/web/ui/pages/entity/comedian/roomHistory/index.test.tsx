/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import RoomHistorySection from "./index";
import type { RoomHistoryDTO } from "@/objects/class/comedian/roomHistory.interface";

vi.mock("next/image", () => ({
    default: ({ alt, src }: { alt: string; src: string }) => (
        <img alt={alt} src={src} />
    ),
}));

vi.mock("next/link", () => ({
    default: ({
        href,
        children,
        ...rest
    }: {
        href: string;
        children: React.ReactNode;
    }) => (
        <a href={href} {...rest}>
            {children}
        </a>
    ),
}));

function makeRoom(over: Partial<RoomHistoryDTO> = {}): RoomHistoryDTO {
    return {
        clubId: 1,
        clubName: "Comedy Cellar",
        clubCity: "NYC",
        clubState: "NY",
        imageUrl: "https://cdn.example.com/Comedy Cellar.png",
        playCount: 3,
        lastPlayedDate: new Date("2025-03-15T20:00:00Z"),
        ...over,
    };
}

describe("RoomHistorySection", () => {
    afterEach(() => cleanup());

    it("renders nothing when the comedian has no club history", () => {
        const { container } = render(
            <RoomHistorySection comedianName="Jane Comic" rooms={[]} />,
        );

        expect(container.firstChild).toBeNull();
    });

    it("renders one tile per club with play count and last-played date", () => {
        const rooms = [
            makeRoom({
                clubId: 10,
                clubName: "Comedy Cellar",
                playCount: 5,
                lastPlayedDate: new Date("2025-04-02T20:00:00Z"),
            }),
            makeRoom({
                clubId: 11,
                clubName: "The Stand",
                clubCity: "NYC",
                clubState: "NY",
                playCount: 1,
                lastPlayedDate: new Date("2023-09-12T20:00:00Z"),
            }),
        ];

        const { getByTestId, getByText } = render(
            <RoomHistorySection comedianName="Jane Comic" rooms={rooms} />,
        );

        const cellarTile = getByTestId("room-history-tile-10");
        expect(cellarTile).toHaveProperty("tagName", "A");
        expect(cellarTile.getAttribute("href")).toBe("/club/Comedy Cellar");
        expect(
            getByText(/Played 5 times · last set Apr 2025/),
        ).not.toBeNull();
        expect(
            getByText(/Played 1 time · last set Sep 2023/),
        ).not.toBeNull();
    });

    it("uses the singular form for clubs with a single play", () => {
        const rooms = [makeRoom({ playCount: 1 })];
        const { getByText } = render(
            <RoomHistorySection comedianName="Jane Comic" rooms={rooms} />,
        );

        expect(getByText(/Played 1 time ·/)).not.toBeNull();
    });

    it("renders tiles in the order they were passed in (data layer presort)", () => {
        const rooms = [
            makeRoom({ clubId: 1, clubName: "First Club", playCount: 9 }),
            makeRoom({ clubId: 2, clubName: "Second Club", playCount: 4 }),
            makeRoom({ clubId: 3, clubName: "Third Club", playCount: 1 }),
        ];

        const { container } = render(
            <RoomHistorySection comedianName="Jane Comic" rooms={rooms} />,
        );

        const tiles = container.querySelectorAll(
            "[data-testid^='room-history-tile-']",
        );
        expect(Array.from(tiles).map((t) => t.getAttribute("data-testid"))).toEqual([
            "room-history-tile-1",
            "room-history-tile-2",
            "room-history-tile-3",
        ]);
    });
});
