import { describe, expect, it } from "vitest";
import { buildHeroPaletteFromSamples } from "./heroPalette";

describe("buildHeroPaletteFromSamples", () => {
    it("blends a saturated photo color with cedar instead of returning it directly", () => {
        const palette = buildHeroPaletteFromSamples([
            ...Array.from({ length: 30 }, () => ({
                r: 32,
                g: 120,
                b: 180,
                a: 255,
            })),
            ...Array.from({ length: 8 }, () => ({
                r: 210,
                g: 92,
                b: 48,
                a: 255,
            })),
        ]);

        expect(palette).not.toBeNull();
        expect(palette?.accent).not.toBe("#2078b4");
        expect(palette?.accent).toMatch(/^#[0-9a-f]{6}$/);
        expect(palette?.cta).toMatch(/^#[0-9a-f]{6}$/);
    });

    it("ignores transparent, near-white, and near-black samples", () => {
        const palette = buildHeroPaletteFromSamples([
            { r: 255, g: 255, b: 255, a: 255 },
            { r: 5, g: 5, b: 5, a: 255 },
            { r: 200, g: 10, b: 10, a: 20 },
        ]);

        expect(palette).toBeNull();
    });

    it("uses a separate color for the CTA when a distinct secondary candidate exists", () => {
        const palette = buildHeroPaletteFromSamples([
            ...Array.from({ length: 40 }, () => ({
                r: 42,
                g: 118,
                b: 184,
                a: 255,
            })),
            ...Array.from({ length: 32 }, () => ({
                r: 198,
                g: 88,
                b: 44,
                a: 255,
            })),
        ]);

        expect(palette).not.toBeNull();
        expect(palette?.cta).not.toBe(palette?.accent);
    });
});
