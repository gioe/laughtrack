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
    const cdnBase = `https://${process.env.BUNNYCDN_CDN_HOST}/`
    try {
        return new URL(`/clubs/${encodeURIComponent(clubName)}.png`, cdnBase).toString()
    } catch {
        try {
            return new URL(`logo.png`, cdnBase).toString()
        } catch {
            return ''
        }
    }
};
