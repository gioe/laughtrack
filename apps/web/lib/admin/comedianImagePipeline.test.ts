import { describe, expect, it, vi } from "vitest";
import sharp from "sharp";

import {
    ComedianImageDownloadError,
    buildComedianAssetPaths,
    downloadComedianImage,
    generateComedianImageVariants,
    validateComedianImageUrl,
} from "./comedianImagePipeline";

function imageResponse(body: Uint8Array, contentType = "image/jpeg") {
    return new Response(body, {
        status: 200,
        headers: { "content-type": contentType },
    });
}

async function makePngBuffer(
    width: number,
    height: number,
): Promise<Uint8Array> {
    const buffer = await sharp({
        create: {
            width,
            height,
            channels: 3,
            background: { r: 200, g: 100, b: 50 },
        },
    })
        .png()
        .toBuffer();
    return new Uint8Array(buffer);
}

describe("validateComedianImageUrl", () => {
    it("rejects malformed URLs", () => {
        expect(() => validateComedianImageUrl("not-a-url")).toThrowError(
            ComedianImageDownloadError,
        );
    });

    it("rejects non-http(s) protocols", () => {
        try {
            validateComedianImageUrl("data:image/png;base64,AAAA");
            expect.fail("expected throw");
        } catch (error) {
            expect(error).toBeInstanceOf(ComedianImageDownloadError);
            expect((error as ComedianImageDownloadError).code).toBe(
                "INVALID_PROTOCOL",
            );
        }
    });

    it.each([
        "http://localhost/img.jpg",
        "http://127.0.0.1/img.jpg",
        "http://10.0.0.1/img.jpg",
        "http://192.168.1.1/img.jpg",
        "http://172.17.0.1/img.jpg",
        "http://169.254.169.254/img.jpg",
        "http://0.0.0.0/img.jpg",
        "http://[::1]/img.jpg",
    ])("rejects private/local host %s", (rawUrl) => {
        try {
            validateComedianImageUrl(rawUrl);
            expect.fail(`expected throw for ${rawUrl}`);
        } catch (error) {
            expect(error).toBeInstanceOf(ComedianImageDownloadError);
            expect((error as ComedianImageDownloadError).code).toBe(
                "BLOCKED_HOST",
            );
        }
    });

    it("accepts public https URLs and strips fragments", () => {
        const url = validateComedianImageUrl(
            "https://example.com/img.jpg#frag",
        );
        expect(url.toString()).toBe("https://example.com/img.jpg");
    });
});

describe("downloadComedianImage", () => {
    it("rejects unsafe hosts before issuing a network request", async () => {
        const fetchMock = vi.fn();
        await expect(
            downloadComedianImage("http://127.0.0.1/x.jpg", {
                fetch: fetchMock as never,
            }),
        ).rejects.toMatchObject({
            name: "ComedianImageDownloadError",
            code: "BLOCKED_HOST",
        });
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("rejects non-image content types", async () => {
        const fetchMock = vi.fn(async () =>
            imageResponse(new Uint8Array([1, 2, 3]), "text/html"),
        );
        await expect(
            downloadComedianImage("https://example.com/page", {
                fetch: fetchMock as never,
            }),
        ).rejects.toMatchObject({ code: "INVALID_MIME" });
    });

    it("rejects oversized responses based on content-length", async () => {
        const fetchMock = vi.fn(async () => {
            const body = new Uint8Array([1, 2, 3]);
            return new Response(body, {
                status: 200,
                headers: {
                    "content-type": "image/jpeg",
                    "content-length": String(50 * 1024 * 1024),
                },
            });
        });
        await expect(
            downloadComedianImage("https://example.com/large.jpg", {
                fetch: fetchMock as never,
            }),
        ).rejects.toMatchObject({ code: "TOO_LARGE" });
    });

    it("rejects payloads that sharp cannot decode", async () => {
        const fetchMock = vi.fn(async () =>
            imageResponse(new Uint8Array([1, 2, 3]), "image/jpeg"),
        );
        await expect(
            downloadComedianImage("https://example.com/bad.jpg", {
                fetch: fetchMock as never,
            }),
        ).rejects.toMatchObject({ code: "DECODE_FAILED" });
    });

    it("rejects images below the minimum source dimension", async () => {
        const small = await makePngBuffer(200, 200);
        const fetchMock = vi.fn(async () =>
            imageResponse(small, "image/png"),
        );
        await expect(
            downloadComedianImage("https://example.com/small.png", {
                fetch: fetchMock as never,
            }),
        ).rejects.toMatchObject({ code: "TOO_SMALL" });
    });

    it("returns decoded metadata for a valid image", async () => {
        const good = await makePngBuffer(1200, 1600);
        const fetchMock = vi.fn(async () =>
            imageResponse(good, "image/png"),
        );
        const result = await downloadComedianImage(
            "https://example.com/good.png",
            { fetch: fetchMock as never },
        );
        expect(result.mimeType).toBe("image/png");
        expect(result.width).toBe(1200);
        expect(result.height).toBe(1600);
        expect(result.sourceUrl).toBe("https://example.com/good.png");
        expect(result.buffer.length).toBe(good.length);
    });
});

describe("generateComedianImageVariants", () => {
    it("produces 1000x1000 avatar and 2000x1125 hero JPEG buffers", async () => {
        const source = await makePngBuffer(2400, 2400);
        const variants = await generateComedianImageVariants({
            sourceUrl: "https://example.com/img.png",
            buffer: Buffer.from(source),
            mimeType: "image/png",
            width: 2400,
            height: 2400,
        });

        const avatarMeta = await sharp(variants.avatarBuffer).metadata();
        const heroMeta = await sharp(variants.heroBuffer).metadata();
        expect(avatarMeta.format).toBe("jpeg");
        expect(avatarMeta.width).toBe(1000);
        expect(avatarMeta.height).toBe(1000);
        expect(heroMeta.format).toBe("jpeg");
        expect(heroMeta.width).toBe(2000);
        expect(heroMeta.height).toBe(1125);
    });
});

describe("buildComedianAssetPaths", () => {
    it("uses stable id and slug, never display name, with mime-derived original ext", () => {
        const paths = buildComedianAssetPaths(42, "slug-abc", "image/png");
        expect(paths).toEqual({
            original: "comedian-images/42/slug-abc/original.png",
            avatar: "comedian-images/42/slug-abc/avatar.jpg",
            hero: "comedian-images/42/slug-abc/hero.jpg",
        });
    });

    it("falls back to .bin extension for unknown mime types", () => {
        const paths = buildComedianAssetPaths(42, "slug-abc", "image/tiff");
        expect(paths.original).toBe("comedian-images/42/slug-abc/original.bin");
    });
});
