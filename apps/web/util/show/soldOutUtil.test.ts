import { describe, expect, it } from "vitest";
import { computeShowSoldOut } from "./soldOutUtil";

describe("computeShowSoldOut", () => {
    it("returns true when the title has a sold-out marker even if tickets are available", () => {
        expect(
            computeShowSoldOut(
                "SOLD OUT Ronny Chieng: I Love New York City Tour",
                [{ soldOut: false }],
            ),
        ).toBe(true);
    });

    it("returns true when the title has a sold-out marker and there are no tickets", () => {
        expect(
            computeShowSoldOut("Ali Wong: Work In Progress - SOLD OUT", []),
        ).toBe(true);
    });

    it("does not match unrelated words containing sold", () => {
        expect(
            computeShowSoldOut("Selling Out The Room", [{ soldOut: false }]),
        ).toBe(false);
    });
});
