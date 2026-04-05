const cdnHost = process.env.BUNNYCDN_CDN_HOST;
if (!cdnHost) {
    throw new Error("Missing required environment variable: BUNNYCDN_CDN_HOST");
}

const buildDiceBearUrl = (name: string) =>
    `https://api.dicebear.com/9.x/thumbs/svg?seed=${encodeURIComponent(name)}`;

export const buildComedianImageUrl = (name: string, hasImage = true) => {
    if (!hasImage) return buildDiceBearUrl(name);
    return new URL(
        `/comedians/${encodeURIComponent(name)}.png`,
        `https://${cdnHost}/`,
    ).toString();
};

export const buildClubImageUrl = (clubName: string) => {
    const cdnBase = `https://${cdnHost}/`;
    try {
        return new URL(
            `/clubs/${encodeURIComponent(clubName)}.png`,
            cdnBase,
        ).toString();
    } catch {
        try {
            return new URL(`logo.png`, cdnBase).toString();
        } catch {
            return "";
        }
    }
};
