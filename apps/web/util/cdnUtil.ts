export const getCdnUrl = (imagePath: string) => {
    return new URL(
        imagePath,
        `https://${process.env.BUNNYCDN_CDN_HOST}/assets/`,
    ).toString();
};

export const getLocalCdnUrl = (imagePath: string) => {
    return `https://laughtrack.b-cdn.net/assets/${imagePath}`;
}
