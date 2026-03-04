export const buildComedianImageUrl = (name: string) => {
    const value =  (
        new URL(
            `/comedians/${encodeURIComponent(name)}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        )
    ).toString()
    return value
};

export const buildClubImageUrl = (clubName: string) => {
    try {
        return new URL(
            `/clubs/${encodeURIComponent(clubName)}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ).toString()
    } catch {
        return new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`).toString()
    }
};
