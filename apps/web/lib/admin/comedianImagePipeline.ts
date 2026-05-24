import sharp from "sharp";

export const MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024;
export const MIN_SOURCE_DIMENSION = 600;
export const AVATAR_SIZE = 1000;
export const HERO_WIDTH = 2000;
export const HERO_HEIGHT = 1125;
export const JPEG_QUALITY = 85;

const ALLOWED_MIME_TYPES = new Set([
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/avif",
    "image/gif",
]);

const MIME_EXTENSION: Record<string, string> = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
    "image/gif": "gif",
};

export type ComedianImageDownloadCode =
    | "INVALID_URL"
    | "INVALID_PROTOCOL"
    | "BLOCKED_HOST"
    | "HTTP_ERROR"
    | "INVALID_MIME"
    | "TOO_LARGE"
    | "DECODE_FAILED"
    | "TOO_SMALL";

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

export type DownloadComedianImageOptions = {
    fetch?: typeof fetch;
};

function isBlockedHostname(hostname: string): boolean {
    const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
    if (!host) return true;
    if (host === "localhost" || host.endsWith(".localhost")) return true;
    if (host === "::1" || host === "0:0:0:0:0:0:0:1") return true;
    if (host === "0.0.0.0") return true;

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
    return MIME_EXTENSION[mimeType] ?? "bin";
}

export async function downloadComedianImage(
    imageUrl: string,
    options: DownloadComedianImageOptions = {},
): Promise<DownloadedComedianImage> {
    const fetchImpl = options.fetch ?? fetch;
    const url = validateComedianImageUrl(imageUrl);

    const response = await fetchImpl(url.toString(), {
        headers: {
            accept: "image/jpeg,image/png,image/webp,image/avif,image/gif",
        },
    });
    if (!response.ok) {
        throw new ComedianImageDownloadError(
            "HTTP_ERROR",
            `Image fetch failed with HTTP ${response.status}`,
        );
    }
    const contentType =
        response.headers
            .get("content-type")
            ?.split(";")[0]
            ?.trim()
            .toLowerCase() ?? "";
    if (!ALLOWED_MIME_TYPES.has(contentType)) {
        throw new ComedianImageDownloadError(
            "INVALID_MIME",
            `Unsupported content type: ${contentType || "<missing>"}`,
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
    const arrayBuffer = await response.arrayBuffer();
    if (arrayBuffer.byteLength > MAX_DOWNLOAD_BYTES) {
        throw new ComedianImageDownloadError(
            "TOO_LARGE",
            `Image body ${arrayBuffer.byteLength} bytes exceeds limit of ${MAX_DOWNLOAD_BYTES}`,
        );
    }
    const buffer = Buffer.from(arrayBuffer);

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

    return {
        sourceUrl: url.toString(),
        buffer,
        mimeType: contentType,
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
