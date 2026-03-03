export const buildComedianImageUrl = (name: string) => {
    const value =  (
        new URL(
            `/comedians/${name}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        )
    ).toString()
    return value
};

export const buildClubImageUrl = (clubName: string) => {
    return (
        new URL(
            `/clubs/${clubName}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    ).toString()
};
