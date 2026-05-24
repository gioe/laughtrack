import { buildComedianImageUrl } from "@/util/imageUtil";

export type ComedianImageAssetForUrl = {
    avatarPath?: string | null;
    heroPath?: string | null;
    isActive?: boolean | null;
};

type BuildComedianImageUrlsInput = {
    name: string;
    hasImage?: boolean | null;
    activeAsset?: ComedianImageAssetForUrl | null;
};

export type ComedianImageUrls = {
    imageUrl: string;
    avatarUrl: string;
    heroUrl: string;
};

const cdnHost = process.env.BUNNYCDN_CDN_HOST;
if (!cdnHost) {
    throw new Error("Missing required environment variable: BUNNYCDN_CDN_HOST");
}

export function buildComedianImageAssetUrl(path: string): string {
    return new URL(path.replace(/^\/+/, ""), `https://${cdnHost}/`).toString();
}

export function buildComedianImageUrls({
    name,
    hasImage,
    activeAsset,
}: BuildComedianImageUrlsInput): ComedianImageUrls {
    const legacyUrl = buildComedianImageUrl(name, Boolean(hasImage));
    const asset =
        activeAsset && activeAsset.isActive !== false ? activeAsset : null;
    const avatarUrl = asset?.avatarPath
        ? buildComedianImageAssetUrl(asset.avatarPath)
        : legacyUrl;
    const heroUrl = asset?.heroPath
        ? buildComedianImageAssetUrl(asset.heroPath)
        : legacyUrl;

    return {
        imageUrl: avatarUrl,
        avatarUrl,
        heroUrl,
    };
}
