/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import ClubShowRooms, { groupShowsByRoom, hasMultipleRooms } from "./index";

vi.mock("@/ui/pages/search/table", () => ({
    default: ({
        shows,
        hideClubName,
    }: {
        shows: ShowDTO[];
        hideClubName?: boolean;
    }) => (
        <div
            data-testid="show-table"
            data-show-ids={shows.map((show) => show.id).join(",")}
            data-hide-club-name={String(hideClubName)}
        />
    ),
}));

afterEach(() => {
    cleanup();
});

const makeShow = (id: number, room?: string | null): ShowDTO => ({
    id,
    clubID: 1,
    clubName: "Comedy Cellar",
    date: "2026-05-20T20:00:00Z" as never as Date,
    tickets: [],
    name: "Late show",
    lineup: [],
    address: "117 MacDougal St",
    room,
    imageUrl: "/placeholders/club-placeholder.svg",
    timezone: "America/New_York",
});

describe("ClubShowRooms", () => {
    it("keeps single-room club detail pages as one flat show table", () => {
        render(
            <ClubShowRooms
                shows={[makeShow(1, "Main Room"), makeShow(2, "Main Room")]}
            />,
        );

        expect(screen.getAllByTestId("show-table")).toHaveLength(1);
        expect(screen.queryByRole("heading", { name: "Main Room" })).toBeNull();
    });

    it("groups multi-room club detail pages by room in show order", () => {
        render(
            <ClubShowRooms
                shows={[
                    makeShow(1, "Village Underground"),
                    makeShow(2, "MacDougal St."),
                    makeShow(3, "Village Underground"),
                ]}
            />,
        );

        expect(
            screen.getByRole("heading", { name: "Village Underground" }),
        ).toBeTruthy();
        expect(
            screen.getByRole("heading", { name: "MacDougal St." }),
        ).toBeTruthy();
        expect(screen.getAllByTestId("show-table")).toHaveLength(2);
        expect(screen.getAllByTestId("show-table")[0].dataset.showIds).toBe(
            "1,3",
        );
    });

    it("ignores blank rooms when deciding whether grouping is useful", () => {
        expect(
            hasMultipleRooms([
                makeShow(1, "Village Underground"),
                makeShow(2, " "),
                makeShow(3, null),
            ]),
        ).toBe(false);
    });

    it("preserves unassigned shows in their own group when other rooms vary", () => {
        const groups = groupShowsByRoom([
            makeShow(1, "Village Underground"),
            makeShow(2, null),
            makeShow(3, "MacDougal St."),
        ]);

        expect(groups.map((group) => group.room)).toEqual([
            "Village Underground",
            null,
            "MacDougal St.",
        ]);
    });
});
