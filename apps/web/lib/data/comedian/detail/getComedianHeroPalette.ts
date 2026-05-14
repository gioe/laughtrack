import { unstable_cache } from "next/cache";
import sharp from "sharp";
import { CACHE } from "@/util/constants/cacheConstants";
import {
    buildHeroPaletteFromSamples,
    COMEDIAN_HERO_DEFAULTS,
    PixelSample,
    ComedianHeroPalette,
} from "./heroPalette";

const MAX_IMAGE_BYTES = 4_000_000;
const PALETTE_ALGORITHM_VERSION = "v2";

async function fetchImageBuffer(imageUrl: string) {
    const response = await fetch(imageUrl, { cache: "no-store" });
    if (!response.ok) return null;

    const contentLength = Number(response.headers.get("content-length"));
    if (Number.isFinite(contentLength) && contentLength > MAX_IMAGE_BYTES) {
        return null;
    }

    // Stream the body chunk-by-chunk instead of awaiting response.arrayBuffer()
    // or response.bytes(). Next.js's dev-mode fetch instrumentation wraps the
    // Response and recurses into a stack overflow when those one-shot consumers
    // are awaited inside an RSC render — surfaces as
    // "RangeError: Maximum call stack size exceeded" with no real stack trace,
    // wrapped as "failed to pipe response", killing the first request after a
    // fresh compile of `/comedian/[name]`. The streaming reader path bypasses
    // the wrapper and is byte-equivalent to arrayBuffer().
    if (!response.body) return null;
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (!value) continue;
        chunks.push(value);
        total += value.byteLength;
        if (total > MAX_IMAGE_BYTES) {
            await reader.cancel();
            return null;
        }
    }

    const merged = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.byteLength;
    }
    return Buffer.from(merged);
}

async function extractComedianHeroPalette(imageUrl: string) {
    try {
        const buffer = await fetchImageBuffer(imageUrl);
        if (!buffer) return null;

        const { data } = await sharp(buffer)
            .rotate()
            .resize(36, 36, { fit: "inside", withoutEnlargement: true })
            .ensureAlpha()
            .raw()
            .toBuffer({ resolveWithObject: true });

        const samples: PixelSample[] = [];
        for (let i = 0; i < data.length; i += 4) {
            samples.push({
                r: data[i] ?? 0,
                g: data[i + 1] ?? 0,
                b: data[i + 2] ?? 0,
                a: data[i + 3] ?? 255,
            });
        }

        return buildHeroPaletteFromSamples(samples);
    } catch (error) {
        console.warn("Comedian hero palette extraction failed", {
            imageUrl,
            error,
        });
        return null;
    }
}

async function getImageVersion(comedianId: number, imageUrl: string) {
    const readVersion = unstable_cache(
        async () => {
            try {
                const response = await fetch(imageUrl, { method: "HEAD" });
                return (
                    response.headers.get("etag") ??
                    response.headers.get("last-modified") ??
                    imageUrl
                );
            } catch {
                return imageUrl;
            }
        },
        ["comedian-image-version", String(comedianId), imageUrl],
        {
            revalidate: CACHE.detailPage,
            tags: ["comedian-image-version", String(comedianId)],
        },
    );

    return readVersion();
}

export async function getComedianHeroPalette({
    comedianId,
    imageUrl,
    hasImage,
}: {
    comedianId: number;
    imageUrl: string;
    hasImage?: boolean;
}): Promise<ComedianHeroPalette | null> {
    if (!hasImage || !imageUrl) return null;

    const imageVersion = await getImageVersion(comedianId, imageUrl);
    const getCachedPalette = unstable_cache(
        async () => extractComedianHeroPalette(imageUrl),
        [
            "comedian-hero-palette",
            PALETTE_ALGORITHM_VERSION,
            String(comedianId),
            imageVersion,
        ],
        {
            revalidate: CACHE.detailPage,
            tags: ["comedian-hero-palette", String(comedianId)],
        },
    );

    return (await getCachedPalette()) ?? COMEDIAN_HERO_DEFAULTS;
}
