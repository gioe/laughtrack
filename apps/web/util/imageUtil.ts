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
