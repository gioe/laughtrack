import {
    ASPECT_RATIO_TOLERANCE,
    HEADSHOT_ASPECT_RATIO,
    HERO_ASPECT_RATIO,
    HERO_HEIGHT,
    HERO_WIDTH,
    MIN_SOURCE_DIMENSION,
} from "./comedianImageConstraints";

export type ComedianImageSlot = "headshot" | "hero";

export type ComedianImageValidationResult =
    | { ok: true; width: number; height: number }
    | { ok: false; reason: string };

function expectedRatio(slot: ComedianImageSlot) {
    return slot === "headshot" ? HEADSHOT_ASPECT_RATIO : HERO_ASPECT_RATIO;
}

function ratioLabel(slot: ComedianImageSlot) {
    return slot === "headshot"
        ? "1:1 (square)"
        : `${HERO_WIDTH}x${HERO_HEIGHT} (16:9)`;
}

function slotLabel(slot: ComedianImageSlot) {
    return slot === "headshot" ? "Headshot" : "Hero";
}

export function checkComedianImageDimensions(
    width: number,
    height: number,
    slot: ComedianImageSlot,
): ComedianImageValidationResult {
    if (width < MIN_SOURCE_DIMENSION || height < MIN_SOURCE_DIMENSION) {
        return {
            ok: false,
            reason: `${slotLabel(slot)} is ${width}x${height}; must be at least ${MIN_SOURCE_DIMENSION}x${MIN_SOURCE_DIMENSION}`,
        };
    }
    const actualRatio = width / height;
    if (Math.abs(actualRatio - expectedRatio(slot)) > ASPECT_RATIO_TOLERANCE) {
        return {
            ok: false,
            reason: `${slotLabel(slot)} is ${width}x${height}; must be close to ${ratioLabel(slot)}`,
        };
    }
    return { ok: true, width, height };
}

export async function validateComedianImageFile(
    file: File,
    slot: ComedianImageSlot,
): Promise<ComedianImageValidationResult> {
    const objectUrl = URL.createObjectURL(file);
    try {
        const dims = await new Promise<{
            width: number;
            height: number;
        } | null>((resolve) => {
            const img = new Image();
            img.onload = () =>
                resolve({
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                });
            img.onerror = () => resolve(null);
            img.src = objectUrl;
        });
        if (!dims || !dims.width || !dims.height) {
            return {
                ok: false,
                reason: `${slotLabel(slot)} file could not be decoded — choose a valid JPG, PNG, WebP, or AVIF image`,
            };
        }
        return checkComedianImageDimensions(dims.width, dims.height, slot);
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}
