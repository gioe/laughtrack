import { describe, expect, it } from "vitest";
import { normalizePodcastAppearanceRole } from "./appearanceRole";

describe("normalizePodcastAppearanceRole", () => {
    it.each([
        ["host", "host"],
        [" Host ", "host"],
        ["cohost", "cohost"],
        ["co-host", "cohost"],
        ["co_host", "cohost"],
        ["guest", "guest"],
        ["mention", "guest"],
        ["", "guest"],
        [null, "guest"],
    ] as const)("maps %s to %s", (input, expected) => {
        expect(normalizePodcastAppearanceRole(input)).toBe(expected);
    });
});
