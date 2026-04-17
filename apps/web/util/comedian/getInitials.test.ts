import { describe, it, expect } from "vitest";
import { getInitials } from "./getInitials";

describe("getInitials", () => {
    it("returns first + last word initials for multi-word names", () => {
        expect(getInitials("Mark Normand")).toBe("MN");
        expect(getInitials("Dave A. Smith")).toBe("DS");
        expect(getInitials("Bill Hicks Jr.")).toBe("BJ");
    });

    it("returns up to two letters for single-word names", () => {
        expect(getInitials("Dave")).toBe("DA");
        expect(getInitials("Jo")).toBe("JO");
        expect(getInitials("X")).toBe("X");
    });

    it("uppercases lowercase names", () => {
        expect(getInitials("mark normand")).toBe("MN");
    });

    it("handles null, undefined, empty, and whitespace-only", () => {
        expect(getInitials(null)).toBe("");
        expect(getInitials(undefined)).toBe("");
        expect(getInitials("")).toBe("");
        expect(getInitials("   ")).toBe("");
    });

    it("ignores leading punctuation and quotes", () => {
        expect(getInitials("'Weird Al' Yankovic")).toBe("WY");
        expect(getInitials("(Dr.) Phil")).toBe("DP");
    });

    it("collapses internal whitespace", () => {
        expect(getInitials("Mark    Normand")).toBe("MN");
        expect(getInitials("  Mark Normand  ")).toBe("MN");
    });

    it("handles names with hyphens by treating the hyphenated token as one word", () => {
        expect(getInitials("Anne-Marie Johnson")).toBe("AJ");
    });

    it("supports non-Latin scripts", () => {
        // Cyrillic
        expect(getInitials("Иван Петров")).toBe("ИП");
        // Greek
        expect(getInitials("Γιώργος Παπαδόπουλος")).toBe("ΓΠ");
        // CJK (single word of CJK characters — first two code points)
        expect(getInitials("王小明")).toBe("王小");
    });

    it("returns empty string when name is only punctuation", () => {
        expect(getInitials("...")).toBe("");
        expect(getInitials("!!!")).toBe("");
    });
});
