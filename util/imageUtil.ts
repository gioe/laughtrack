export const buildComedianImageUrl = (name: string, isAlias: boolean) => {
    if (isAlias) {
        return new URL("mystery-comedian-placeholder.png", `https://${process.env.BUNNYCDN_CDN_HOST}/`).toString()
    }

    return (
        new URL(
            `/comedians/${name}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    ).toString()
};

export const buildClubImageUrl = (clubName: string) => {
    return (
        new URL(
            `/clubs/${clubName}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    ).toString()
};
