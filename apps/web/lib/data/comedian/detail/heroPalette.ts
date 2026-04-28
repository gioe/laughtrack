export interface ComedianHeroPalette {
    accent: string;
    accentSoft: string;
    cta: string;
    ctaHover: string;
}

export interface PixelSample {
    r: number;
    g: number;
    b: number;
    a: number;
}

interface ColorCandidate {
    r: number;
    g: number;
    b: number;
    count: number;
    score: number;
}

const CEDAR = "#361E14";
const PAARL = "#A96030";
const COPPER = "#B87333";
const COPPER_HOVER = "#9F5E2A";

export const COMEDIAN_HERO_DEFAULTS: ComedianHeroPalette & { cedar: string } = {
    cedar: CEDAR,
    accent: PAARL,
    accentSoft: "rgba(169, 96, 48, 0.42)",
    cta: COPPER,
    ctaHover: COPPER_HOVER,
};

function clampChannel(value: number) {
    return Math.max(0, Math.min(255, Math.round(value)));
}

function toHex({ r, g, b }: Pick<PixelSample, "r" | "g" | "b">) {
    return `#${[r, g, b]
        .map((channel) => clampChannel(channel).toString(16).padStart(2, "0"))
        .join("")}`;
}

function toRgba(
    { r, g, b }: Pick<PixelSample, "r" | "g" | "b">,
    alpha: number,
) {
    return `rgba(${clampChannel(r)}, ${clampChannel(g)}, ${clampChannel(b)}, ${alpha})`;
}

function luminance({ r, g, b }: Pick<PixelSample, "r" | "g" | "b">) {
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

function saturation({ r, g, b }: Pick<PixelSample, "r" | "g" | "b">) {
    const max = Math.max(r, g, b) / 255;
    const min = Math.min(r, g, b) / 255;
    if (max === 0) return 0;
    return (max - min) / max;
}

function colorDistance(a: ColorCandidate, b: ColorCandidate) {
    return Math.sqrt((a.r - b.r) ** 2 + (a.g - b.g) ** 2 + (a.b - b.b) ** 2);
}

function mixWithCedar(
    color: Pick<PixelSample, "r" | "g" | "b">,
    colorWeight: number,
) {
    return {
        r: 54 * (1 - colorWeight) + color.r * colorWeight,
        g: 30 * (1 - colorWeight) + color.g * colorWeight,
        b: 20 * (1 - colorWeight) + color.b * colorWeight,
    };
}

function chooseCandidates(samples: PixelSample[]) {
    const bins = new Map<string, ColorCandidate>();

    for (const sample of samples) {
        if (sample.a < 200) continue;

        const lum = luminance(sample);
        const sat = saturation(sample);
        if (lum < 0.12 || lum > 0.88 || sat < 0.16) continue;

        const r = Math.round(sample.r / 16) * 16;
        const g = Math.round(sample.g / 16) * 16;
        const b = Math.round(sample.b / 16) * 16;
        const key = `${r}-${g}-${b}`;
        const existing = bins.get(key);

        if (existing) {
            existing.count += 1;
            existing.score += sat * sat * (1 - Math.abs(lum - 0.52));
        } else {
            bins.set(key, {
                r,
                g,
                b,
                count: 1,
                score: sat * sat * (1 - Math.abs(lum - 0.52)),
            });
        }
    }

    return [...bins.values()].sort((a, b) => {
        const scoreDelta = b.score - a.score;
        if (scoreDelta !== 0) return scoreDelta;
        return b.count - a.count;
    });
}

export function buildHeroPaletteFromSamples(
    samples: PixelSample[],
): ComedianHeroPalette | null {
    const candidates = chooseCandidates(samples);
    const primary = candidates[0];
    if (!primary) return null;

    const secondary =
        candidates.find(
            (candidate) => colorDistance(primary, candidate) > 72,
        ) ?? primary;

    const accent = mixWithCedar(primary, 0.58);
    const cta = mixWithCedar(secondary, 0.78);
    const ctaHover = mixWithCedar(secondary, 0.66);

    return {
        accent: toHex(accent),
        accentSoft: toRgba(accent, 0.5),
        cta: toHex(cta),
        ctaHover: toHex(ctaHover),
    };
}
