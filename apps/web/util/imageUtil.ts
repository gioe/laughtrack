const cdnHost = process.env.BUNNYCDN_CDN_HOST;
if (!cdnHost) {
    throw new Error("Missing required environment variable: BUNNYCDN_CDN_HOST");
}

export const buildComedianImageUrl = (name: string, hasImage = true) => {
    if (!hasImage) return "";
    return new URL(
        `/comedians/${encodeURIComponent(name)}.png`,
        `https://${cdnHost}/`,
    ).toString();
};

const CLUB_PLACEHOLDER = "/placeholders/club-placeholder.svg";

export const buildClubImageUrl = (clubName: string, hasImage = true) => {
    if (!hasImage) return CLUB_PLACEHOLDER;
    const cdnBase = `https://${cdnHost}/`;
    try {
        return new URL(
            `/clubs/${encodeURIComponent(clubName)}.png`,
            cdnBase,
        ).toString();
    } catch {
        return CLUB_PLACEHOLDER;
    }
};

export const buildClubImageAssetUrl = (path: string) => {
    if (/^(?:[a-z][a-z0-9+.-]*:)?\/\//i.test(path)) {
        throw new Error("Club image asset path must be CDN-relative");
    }
    return new URL(path.replace(/^\/+/, ""), `https://${cdnHost}/`).toString();
};

export const buildClubHeroImageUrl = (heroPath?: string | null) => {
    if (!heroPath) return "";
    try {
        return buildClubImageAssetUrl(heroPath);
    } catch {
        return "";
    }
};
