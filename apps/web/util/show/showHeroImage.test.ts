import { describe, expect, it } from "vitest";
import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import type { SocialDataDTO } from "@/objects/class/socialData/socialData.interface";
import { inferHeadliner, showHeroImage } from "./showHeroImage";

const CLUB_IMAGE = "https://cdn.example.com/clubs/The%20Copper%20Room.png";

const comedian = (
    name: string,
    overrides: Partial<ComedianLineupDTO> = {},
): ComedianLineupDTO => ({
    id: name.length,
    uuid: `uuid-${name}`,
    name,
    imageUrl: `https://cdn.example.com/comedians/${encodeURIComponent(name)}.png`,
    ...overrides,
});

const socialData = (popularity: number | null): SocialDataDTO =>
    ({ popularity }) as SocialDataDTO;

const show = (lineup: ComedianLineupDTO[], tags?: { slug: string; name: string }[]) => ({
    imageUrl: CLUB_IMAGE,
    lineup,
    ...(tags ? { tags } : {}),
});

describe("inferHeadliner", () => {
    it("picks the highest socialData.popularity", () => {
        const winner = comedian("Big Pop", { socialData: socialData(90) });
        const result = inferHeadliner(
            show([
                comedian("Small Pop", { socialData: socialData(10) }),
                winner,
                comedian("Mid Pop", { socialData: socialData(50) }),
            ]),
        );
        expect(result?.name).toBe("Big Pop");
    });

    it("breaks popularity ties by showCount", () => {
        const result = inferHeadliner(
            show([
                comedian("Fewer Shows", {
                    socialData: socialData(50),
                    showCount: 8,
                }),
                comedian("More Shows", {
                    socialData: socialData(50),
                    showCount: 98,
                }),
            ]),
        );
        expect(result?.name).toBe("More Shows");
    });

    it("breaks popularity and showCount ties by list position", () => {
        const result = inferHeadliner(
            show([
                comedian("First Billed", { showCount: 12 }),
                comedian("Second Billed", { showCount: 12 }),
            ]),
        );
        expect(result?.name).toBe("First Billed");
    });

    it("ranks missing socialData as -1, below an explicit popularity of 0", () => {
        // Mirrors the iOS `?? -1`: with socialData absent across the board
        // (the live API today), showCount decides — but an explicit 0 must
        // still beat a missing one.
        const result = inferHeadliner(
            show([
                comedian("No Social Data", { showCount: 98 }),
                comedian("Explicit Zero", {
                    socialData: socialData(0),
                    showCount: 1,
                }),
            ]),
        );
        expect(result?.name).toBe("Explicit Zero");
    });

    it("treats null popularity like missing socialData", () => {
        const result = inferHeadliner(
            show([
                comedian("Null Pop", {
                    socialData: socialData(null),
                    showCount: 5,
                }),
                comedian("Real Pop", { socialData: socialData(1) }),
            ]),
        );
        expect(result?.name).toBe("Real Pop");
    });

    it("returns null for open mics", () => {
        expect(
            inferHeadliner(
                show(
                    [comedian("Mic Regular", { showCount: 40 })],
                    [{ slug: "open mic", name: "Open Mic" }],
                ),
            ),
        ).toBeNull();
    });

    it("returns null for empty and missing lineups", () => {
        expect(inferHeadliner(show([]))).toBeNull();
        expect(inferHeadliner({ imageUrl: CLUB_IMAGE })).toBeNull();
    });

    it("does not mutate the lineup order", () => {
        const lineup = [
            comedian("A", { showCount: 1 }),
            comedian("B", { showCount: 99 }),
        ];
        inferHeadliner(show(lineup));
        expect(lineup.map((c) => c.name)).toEqual(["A", "B"]);
    });
});

describe("showHeroImage", () => {
    it("returns the headliner headshot with the headliner attached", () => {
        const hero = showHeroImage(
            show([
                comedian("Opener", { showCount: 8 }),
                comedian("Mark Normand", { showCount: 98 }),
            ]),
        );
        expect(hero.src).toBe(
            "https://cdn.example.com/comedians/Mark%20Normand.png",
        );
        expect(hero.headliner?.name).toBe("Mark Normand");
    });

    it("falls back to the club image when the headliner has no headshot", () => {
        // buildComedianImageUrl emits "" when hasImage is false — the iOS
        // isEmpty fallback must kick in rather than rendering a blank src.
        const hero = showHeroImage(
            show([
                comedian("Imageless Star", { imageUrl: "", showCount: 98 }),
                comedian("Opener", { showCount: 8 }),
            ]),
        );
        expect(hero.src).toBe(CLUB_IMAGE);
        expect(hero.headliner).toBeNull();
    });

    it("falls back to the club image for open mics and empty lineups", () => {
        expect(
            showHeroImage(
                show(
                    [comedian("Mic Regular")],
                    [{ slug: "open mic", name: "Open Mic" }],
                ),
            ),
        ).toEqual({ src: CLUB_IMAGE, headliner: null });
        expect(showHeroImage(show([]))).toEqual({
            src: CLUB_IMAGE,
            headliner: null,
        });
    });
});
