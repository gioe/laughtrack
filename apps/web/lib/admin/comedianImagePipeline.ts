import net from "node:net";
import sharp from "sharp";

export const MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024;
export const MIN_SOURCE_DIMENSION = 600;
export const AVATAR_SIZE = 1000;
export const HERO_WIDTH = 2000;
export const HERO_HEIGHT = 1125;
export const JPEG_QUALITY = 85;
export const DOWNLOAD_TIMEOUT_MS = 15_000;
const ASPECT_RATIO_TOLERANCE = 0.05;

const ALLOWED_MIME_TYPES = new Set([
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/avif",
    "image/gif",
]);

// Map sharp's `metadata.format` token to the canonical MIME type so we can
// cross-check the response's declared Content-Type against the actually-decoded
// pixels and refuse format-spoofing payloads.
const SHARP_FORMAT_MIME: Record<string, string> = {
    jpeg: "image/jpeg",
    jpg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
    avif: "image/avif",
    gif: "image/gif",
};

const SHARP_FORMAT_EXTENSION: Record<string, string> = {
    jpeg: "jpg",
    jpg: "jpg",
    png: "png",
    webp: "webp",
    avif: "avif",
    gif: "gif",
};

const ipv6BlockList = (() => {
    const list = new net.BlockList();
    list.addAddress("::1", "ipv6");
    list.addSubnet("fc00::", 7, "ipv6");
    list.addSubnet("fe80::", 10, "ipv6");
    // IPv4-mapped IPv6 (::ffff:0:0/96) — covers `[::ffff:127.0.0.1]` and any
    // other dual-stack form that would otherwise bypass dotted-decimal checks.
    list.addSubnet("::ffff:0:0", 96, "ipv6");
    return list;
})();

export type ComedianImageDownloadCode =
    | "INVALID_URL"
    | "INVALID_PROTOCOL"
    | "BLOCKED_HOST"
    | "REDIRECT_BLOCKED"
    | "TIMEOUT"
    | "HTTP_ERROR"
    | "INVALID_MIME"
    | "TOO_LARGE"
    | "DECODE_FAILED"
    | "TOO_SMALL"
    | "ANIMATED_NOT_SUPPORTED"
    | "INVALID_ASPECT_RATIO";

export class ComedianImageDownloadError extends Error {
    public readonly code: ComedianImageDownloadCode;

    constructor(code: ComedianImageDownloadCode, message: string) {
        super(message);
        this.name = "ComedianImageDownloadError";
        this.code = code;
    }
}

export type DownloadedComedianImage = {
    sourceUrl: string;
    buffer: Buffer;
    mimeType: string;
    width: number;
    height: number;
};

export type ComedianImageVariants = {
    avatarBuffer: Buffer;
    heroBuffer: Buffer;
};

export type ClubImageVariants = {
    iconBuffer: Buffer;
    heroBuffer: Buffer;
};

export type DownloadComedianImageOptions = {
    fetch?: typeof fetch;
};

function isWithinAspectRatio(
    image: Pick<DownloadedComedianImage, "width" | "height">,
    expectedRatio: number,
) {
    const actualRatio = image.width / image.height;
    return Math.abs(actualRatio - expectedRatio) <= ASPECT_RATIO_TOLERANCE;
}

export function validateComedianImageAspectRatios({
    headshot,
    hero,
}: {
    headshot: DownloadedComedianImage;
    hero?: DownloadedComedianImage;
}) {
    if (!isWithinAspectRatio(headshot, 1)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Headshot source ${headshot.width}x${headshot.height} must be close to a square 1:1 ratio`,
        );
    }

    if (hero && !isWithinAspectRatio(hero, HERO_WIDTH / HERO_HEIGHT)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Hero source ${hero.width}x${hero.height} must be close to a 16:9 ratio`,
        );
    }
}

export function validateComedianHeadshotAspectRatio(
    headshot: DownloadedComedianImage,
) {
    if (!isWithinAspectRatio(headshot, 1)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Headshot source ${headshot.width}x${headshot.height} must be close to a square 1:1 ratio`,
        );
    }
}

export function validateComedianHeroAspectRatio(hero: DownloadedComedianImage) {
    if (!isWithinAspectRatio(hero, HERO_WIDTH / HERO_HEIGHT)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Hero source ${hero.width}x${hero.height} must be close to a 16:9 ratio`,
        );
    }
}

export function validateClubImageAspectRatios({
    icon,
    hero,
}: {
    icon: DownloadedComedianImage;
    hero: DownloadedComedianImage;
}) {
    if (!isWithinAspectRatio(icon, 1)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Icon source ${icon.width}x${icon.height} must be close to a square 1:1 ratio`,
        );
    }

    if (!isWithinAspectRatio(hero, HERO_WIDTH / HERO_HEIGHT)) {
        throw new ComedianImageDownloadError(
            "INVALID_ASPECT_RATIO",
            `Hero source ${hero.width}x${hero.height} must be close to a 16:9 ratio`,
        );
    }
}

function isBlockedHostname(hostname: string): boolean {
    const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
    if (!host) return true;
    if (host === "localhost" || host.endsWith(".localhost")) return true;

    if (net.isIPv6(host)) {
        if (ipv6BlockList.check(host, "ipv6")) return true;
        return false;
    }

    if (host === "0.0.0.0") return true;

    // WHATWG URL parsing canonicalizes integer/octal/hex IPv4 forms
    // (e.g. `http://2130706433/` → `127.0.0.1`), so by the time we get here
    // any IPv4 host is in dotted-decimal form.
    const octets = host.split(".").map((part) => Number(part));
    if (
        octets.length !== 4 ||
        octets.some(
            (octet) => !Number.isInteger(octet) || octet < 0 || octet > 255,
        )
    ) {
        return false;
    }

    const [a, b] = octets;
    return (
        a === 10 ||
        a === 127 ||
        (a === 169 && b === 254) ||
        (a === 172 && b >= 16 && b <= 31) ||
        (a === 192 && b === 168)
    );
}

export function validateComedianImageUrl(rawUrl: string): URL {
    let parsed: URL;
    try {
        parsed = new URL(rawUrl);
    } catch {
        throw new ComedianImageDownloadError(
            "INVALID_URL",
            "Image URL is not a valid URL",
        );
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        throw new ComedianImageDownloadError(
            "INVALID_PROTOCOL",
            "Image URL must use http or https",
        );
    }
    if (isBlockedHostname(parsed.hostname)) {
        throw new ComedianImageDownloadError(
            "BLOCKED_HOST",
            "Image host is not allowed",
        );
    }
    parsed.hash = "";
    return parsed;
}

export function getMimeExtension(mimeType: string): string {
    // sharp-format tokens take precedence; fall back to raw MIME match.
    const sharpExt =
        SHARP_FORMAT_EXTENSION[mimeType.replace(/^image\//, "")] ?? null;
    if (sharpExt) return sharpExt;
    const fromMime: Record<string, string> = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/avif": "avif",
        "image/gif": "gif",
    };
    return fromMime[mimeType] ?? "bin";
}

async function readBodyWithLimit(
    response: Response,
    maxBytes: number,
): Promise<Buffer> {
    const reader = response.body?.getReader();
    if (!reader) {
        // No streaming body (e.g. mocked Response without ReadableStream).
        // Fall back to arrayBuffer with the same post-hoc check; not ideal
        // but safe because the mock body is in-process.
        const fallback = await response.arrayBuffer();
        if (fallback.byteLength > maxBytes) {
            throw new ComedianImageDownloadError(
                "TOO_LARGE",
                `Image body ${fallback.byteLength} bytes exceeds limit of ${maxBytes}`,
            );
        }
        return Buffer.from(fallback);
    }

    const chunks: Buffer[] = [];
    let total = 0;
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            total += value.byteLength;
            if (total > maxBytes) {
                throw new ComedianImageDownloadError(
                    "TOO_LARGE",
                    `Image body exceeded ${maxBytes} bytes mid-stream`,
                );
            }
            chunks.push(Buffer.from(value));
        }
    } finally {
        try {
            await reader.cancel();
        } catch {
            // reader already closed; nothing to do
        }
    }
    return Buffer.concat(chunks);
}

export async function downloadComedianImage(
    imageUrl: string,
    options: DownloadComedianImageOptions = {},
): Promise<DownloadedComedianImage> {
    const fetchImpl = options.fetch ?? fetch;
    const url = validateComedianImageUrl(imageUrl);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DOWNLOAD_TIMEOUT_MS);
    let response: Response;
    try {
        response = await fetchImpl(url.toString(), {
            headers: {
                accept: "image/jpeg,image/png,image/webp,image/avif,image/gif",
            },
            // Refuse redirects entirely — following them re-introduces SSRF
            // because the redirect target hostname is not re-validated.
            // Admins paste candidate URLs after the discovery crawl, so the
            // canonical image URL is expected to serve 200 directly.
            redirect: "error",
            signal: controller.signal,
        });
    } catch (error) {
        if ((error as { name?: string }).name === "AbortError") {
            throw new ComedianImageDownloadError(
                "TIMEOUT",
                `Image fetch timed out after ${DOWNLOAD_TIMEOUT_MS}ms`,
            );
        }
        // node fetch surfaces redirect refusals via TypeError("redirect").
        const msg = (error as Error).message ?? "";
        if (/redirect/i.test(msg)) {
            throw new ComedianImageDownloadError(
                "REDIRECT_BLOCKED",
                "Image URL issued a redirect; redirects are not followed",
            );
        }
        throw error;
    } finally {
        clearTimeout(timeout);
    }

    if (!response.ok) {
        throw new ComedianImageDownloadError(
            "HTTP_ERROR",
            `Image fetch failed with HTTP ${response.status}`,
        );
    }
    const declaredContentType =
        response.headers
            .get("content-type")
            ?.split(";")[0]
            ?.trim()
            .toLowerCase() ?? "";
    if (!ALLOWED_MIME_TYPES.has(declaredContentType)) {
        throw new ComedianImageDownloadError(
            "INVALID_MIME",
            `Unsupported content type: ${declaredContentType || "<missing>"}`,
        );
    }
    const contentLengthHeader = response.headers.get("content-length");
    if (
        contentLengthHeader &&
        Number(contentLengthHeader) > MAX_DOWNLOAD_BYTES
    ) {
        throw new ComedianImageDownloadError(
            "TOO_LARGE",
            `Image declares ${contentLengthHeader} bytes, exceeds limit of ${MAX_DOWNLOAD_BYTES}`,
        );
    }

    const buffer = await readBodyWithLimit(response, MAX_DOWNLOAD_BYTES);

    let metadata: sharp.Metadata;
    try {
        metadata = await sharp(buffer).metadata();
    } catch {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            "Image could not be decoded",
        );
    }
    const width = metadata.width ?? 0;
    const height = metadata.height ?? 0;
    if (width === 0 || height === 0) {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            "Image has no decodable dimensions",
        );
    }
    if (width < MIN_SOURCE_DIMENSION || height < MIN_SOURCE_DIMENSION) {
        throw new ComedianImageDownloadError(
            "TOO_SMALL",
            `Image is ${width}x${height}; must be at least ${MIN_SOURCE_DIMENSION}x${MIN_SOURCE_DIMENSION}`,
        );
    }

    // Cross-check the decoded format against the declared Content-Type so a
    // server that claims `image/jpeg` while serving script bytes cannot pass
    // validation just because the body happens to start with a recognizable
    // magic header in some other format.
    const decodedFormat = metadata.format ?? "";
    const decodedMime = SHARP_FORMAT_MIME[decodedFormat] ?? null;
    if (!decodedMime) {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            `Image decoded to unsupported format "${decodedFormat || "<unknown>"}"`,
        );
    }
    const declaredMimeNormalized =
        declaredContentType === "image/jpg"
            ? "image/jpeg"
            : declaredContentType;
    if (decodedMime !== declaredMimeNormalized) {
        throw new ComedianImageDownloadError(
            "INVALID_MIME",
            `Declared content-type ${declaredContentType} does not match decoded format ${decodedFormat}`,
        );
    }

    // Reject animated source images so admins do not accidentally publish a
    // frozen first frame for sharp's avatar/hero variants. The metadata.pages
    // field is only populated for animated GIF/WebP/AVIF; still images report
    // 0, 1, or undefined.
    if ((metadata.pages ?? 1) > 1) {
        throw new ComedianImageDownloadError(
            "ANIMATED_NOT_SUPPORTED",
            `Animated source images are not supported (${metadata.pages} frames detected)`,
        );
    }

    return {
        sourceUrl: url.toString(),
        buffer,
        mimeType: decodedMime,
        width,
        height,
    };
}

export async function readUploadedComedianImage(
    file: File,
): Promise<DownloadedComedianImage> {
    const declaredContentType = file.type.trim().toLowerCase();
    if (!ALLOWED_MIME_TYPES.has(declaredContentType)) {
        throw new ComedianImageDownloadError(
            "INVALID_MIME",
            `Unsupported content type: ${declaredContentType || "<missing>"}`,
        );
    }
    if (file.size > MAX_DOWNLOAD_BYTES) {
        throw new ComedianImageDownloadError(
            "TOO_LARGE",
            `Image body ${file.size} bytes exceeds limit of ${MAX_DOWNLOAD_BYTES}`,
        );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    let metadata: sharp.Metadata;
    try {
        metadata = await sharp(buffer).metadata();
    } catch {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            "Image could not be decoded",
        );
    }

    const width = metadata.width ?? 0;
    const height = metadata.height ?? 0;
    if (width === 0 || height === 0) {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            "Image has no decodable dimensions",
        );
    }
    if (width < MIN_SOURCE_DIMENSION || height < MIN_SOURCE_DIMENSION) {
        throw new ComedianImageDownloadError(
            "TOO_SMALL",
            `Image is ${width}x${height}; must be at least ${MIN_SOURCE_DIMENSION}x${MIN_SOURCE_DIMENSION}`,
        );
    }

    const decodedFormat = metadata.format ?? "";
    const decodedMime = SHARP_FORMAT_MIME[decodedFormat] ?? null;
    if (!decodedMime) {
        throw new ComedianImageDownloadError(
            "DECODE_FAILED",
            `Image decoded to unsupported format "${decodedFormat || "<unknown>"}"`,
        );
    }
    const declaredMimeNormalized =
        declaredContentType === "image/jpg"
            ? "image/jpeg"
            : declaredContentType;
    if (decodedMime !== declaredMimeNormalized) {
        throw new ComedianImageDownloadError(
            "INVALID_MIME",
            `Declared content-type ${declaredContentType} does not match decoded format ${decodedFormat}`,
        );
    }
    if ((metadata.pages ?? 1) > 1) {
        throw new ComedianImageDownloadError(
            "ANIMATED_NOT_SUPPORTED",
            `Animated source images are not supported (${metadata.pages} frames detected)`,
        );
    }

    return {
        sourceUrl: `upload:${file.name || "image"}`,
        buffer,
        mimeType: decodedMime,
        width,
        height,
    };
}

export async function generateComedianImageVariants(
    image: DownloadedComedianImage,
): Promise<ComedianImageVariants> {
    const avatarBuffer = await sharp(image.buffer)
        .resize(AVATAR_SIZE, AVATAR_SIZE, {
            fit: "cover",
            position: sharp.strategy.attention,
        })
        .jpeg({ quality: JPEG_QUALITY, progressive: true })
        .toBuffer();
    const heroBuffer = await sharp(image.buffer)
        .resize(HERO_WIDTH, HERO_HEIGHT, {
            fit: "cover",
            position: sharp.strategy.attention,
        })
        .jpeg({ quality: JPEG_QUALITY, progressive: true })
        .toBuffer();
    return { avatarBuffer, heroBuffer };
}

export async function generateClubImageVariants({
    icon,
    hero,
}: {
    icon: DownloadedComedianImage;
    hero: DownloadedComedianImage;
}): Promise<ClubImageVariants> {
    const iconBuffer = await sharp(icon.buffer)
        .resize(AVATAR_SIZE, AVATAR_SIZE, {
            fit: "cover",
            position: sharp.strategy.attention,
        })
        .png()
        .toBuffer();
    const heroBuffer = await sharp(hero.buffer)
        .resize(HERO_WIDTH, HERO_HEIGHT, {
            fit: "cover",
            position: sharp.strategy.attention,
        })
        .jpeg({ quality: JPEG_QUALITY, progressive: true })
        .toBuffer();
    return { iconBuffer, heroBuffer };
}

export function buildComedianAssetPaths(
    comedianId: number,
    assetSlug: string,
    sourceMimeType: string,
) {
    const base = `comedian-images/${comedianId}/${assetSlug}`;
    return {
        original: `${base}/original.${getMimeExtension(sourceMimeType)}`,
        avatar: `${base}/avatar.jpg`,
        hero: `${base}/hero.jpg`,
    };
}
