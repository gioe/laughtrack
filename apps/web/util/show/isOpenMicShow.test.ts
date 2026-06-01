import { describe, expect, it } from "vitest";
import { isOpenMicShow, OPEN_MIC_SLUG } from "./isOpenMicShow";

describe("isOpenMicShow", () => {
    it("returns true when tags include the canonical 'open mic' slug", () => {
        expect(
            isOpenMicShow({
                tags: [{ slug: "open mic", name: "Open Mic" }],
            }),
        ).toBe(true);
    });

    it("returns false for missing or empty tags", () => {
        expect(isOpenMicShow({})).toBe(false);
        expect(isOpenMicShow({ tags: undefined })).toBe(false);
        expect(isOpenMicShow({ tags: [] })).toBe(false);
    });

    it("does not match the kebab variant — the canonical slug has a space", () => {
        expect(
            isOpenMicShow({
                tags: [{ slug: "open-mic", name: "Open Mic" }],
            }),
        ).toBe(false);
    });

    it("pins the canonical slug literal to a SPACE (TASK-2546)", () => {
        expect(OPEN_MIC_SLUG).toBe("open mic");
    });
});
