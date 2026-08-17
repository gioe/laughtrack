import { describe, expect, it } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import {
    selectDiverseShowItemsByTime,
    selectDiverseShowsByTime,
} from "./showRailSelection";

function show(id: number, date: string, headlinerId?: number): ShowDTO {
    return {
        id,
        clubId: 1,
        date: new Date(date),
        name: `Show ${id}`,
        imageUrl: "",
        lineup:
            headlinerId === undefined
                ? []
                : [
                      {
                          id: headlinerId,
                          uuid: `comedian-${headlinerId}`,
                          name: `Comedian ${headlinerId}`,
                          imageUrl: "",
                      },
                  ],
    };
}

describe("selectDiverseShowsByTime", () => {
    it("prefers distinct headliners while preserving chronological order", () => {
        const result = selectDiverseShowsByTime(
            [
                show(4, "2026-08-17T12:00:00Z", 3),
                show(2, "2026-08-17T10:30:00Z", 1),
                show(3, "2026-08-17T11:00:00Z", 2),
                show(1, "2026-08-17T10:00:00Z", 1),
            ],
            3,
        );

        expect(result.map(({ id }) => id)).toEqual([1, 3, 4]);
    });

    it("backfills repeated headliners and re-sorts the final rail by time", () => {
        const result = selectDiverseShowsByTime(
            [
                show(4, "2026-08-17T11:30:00Z", 2),
                show(2, "2026-08-17T10:30:00Z", 1),
                show(3, "2026-08-17T11:00:00Z", 2),
                show(1, "2026-08-17T10:00:00Z", 1),
            ],
            4,
        );

        expect(result.map(({ id }) => id)).toEqual([1, 2, 3, 4]);
    });

    it("uses show id as the stable tiebreaker for equal start times", () => {
        const result = selectDiverseShowsByTime(
            [show(9, "2026-08-17T10:00:00Z"), show(4, "2026-08-17T10:00:00Z")],
            2,
        );

        expect(result.map(({ id }) => id)).toEqual([4, 9]);
    });

    it("can limit a rail to one show per exact timestamp", () => {
        const result = selectDiverseShowsByTime(
            [
                show(1, "2026-08-17T20:00:00Z", 1),
                show(2, "2026-08-17T20:00:00Z", 2),
                show(3, "2026-08-17T20:30:00Z", 3),
                show(4, "2026-08-17T21:00:00Z", 4),
            ],
            3,
            { maxPerTimestamp: 1 },
        );

        expect(result.map(({ id }) => id)).toEqual([1, 3, 4]);
    });

    it("prefers a new headliner when backfilling a timestamp slot", () => {
        const result = selectDiverseShowsByTime(
            [
                show(1, "2026-08-17T19:00:00Z", 1),
                show(2, "2026-08-17T20:00:00Z", 1),
                show(3, "2026-08-17T20:00:00Z", 2),
                show(4, "2026-08-17T21:00:00Z", 3),
            ],
            3,
            { maxPerTimestamp: 1 },
        );

        expect(result.map(({ id }) => id)).toEqual([1, 3, 4]);
    });

    it("applies the same selection rule to wrapped dynamic-rail items", () => {
        const items = [
            { show: show(2, "2026-08-17T10:30:00Z", 1), reason: "second" },
            { show: show(3, "2026-08-17T11:00:00Z", 2), reason: "third" },
            { show: show(1, "2026-08-17T10:00:00Z", 1), reason: "first" },
            { show: show(4, "2026-08-17T12:00:00Z", 3), reason: "fourth" },
        ];

        const result = selectDiverseShowItemsByTime(
            items,
            ({ show }) => show,
            3,
        );

        expect(result.map(({ show }) => show.id)).toEqual([1, 3, 4]);
        expect(result.map(({ reason }) => reason)).toEqual([
            "first",
            "third",
            "fourth",
        ]);
    });
});
