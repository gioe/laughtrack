import { describe, expect, it } from "vitest";
import {
    getClubProgrammingFilterOptions,
    getClubProgrammingLabel,
} from "./programmingLabels";

describe("club programming labels", () => {
    it.each([
        [
            { clubType: "club", primaryShowType: "standup" },
            "Stand-up comedy club",
        ],
        [
            { clubType: "venue", primaryShowType: "standup" },
            "Stand-up comedy venue",
        ],
        [{ clubType: "venue", primaryShowType: "improv" }, "Improv theater"],
        [
            { clubType: "venue", primaryShowType: "theater" },
            "Theater with comedy",
        ],
        [
            { clubType: "venue", primaryShowType: "music" },
            "Music venue with comedy",
        ],
        [
            {
                clubType: "venue",
                primaryShowType: null,
                mixedProgramming: true,
            },
            "Mixed comedy venue",
        ],
        [{ clubType: "festival" }, "Comedy festival"],
        [{ clubType: "producer" }, "Comedy producer"],
    ])("maps normalized fields %j to %s", (input, expected) => {
        expect(getClubProgrammingLabel(input)).toBe(expected);
    });

    it("marks synthetic programming options from the filters param", () => {
        expect(
            getClubProgrammingFilterOptions("standup,producer").map(
                ({ slug, name, selected }) => ({ slug, name, selected }),
            ),
        ).toEqual([
            { slug: "standup", name: "Stand-up clubs", selected: true },
            { slug: "improv", name: "Improv theaters", selected: false },
            {
                slug: "theater",
                name: "Theaters with comedy",
                selected: false,
            },
            {
                slug: "music",
                name: "Music venues with comedy",
                selected: false,
            },
            {
                slug: "mixed_programming",
                name: "Mixed comedy venues",
                selected: false,
            },
            { slug: "festival", name: "Festivals", selected: false },
            { slug: "producer", name: "Producers", selected: true },
        ]);
    });

    it("does not mark programming options selected by substring matches", () => {
        expect(
            getClubProgrammingFilterOptions(
                "standup-special,producer-series",
            ).some((filter) => filter.selected),
        ).toBe(false);
    });
});
