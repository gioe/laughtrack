export function googleProviderConfig() {
    return {
        clientId:
            process.env.AUTH_GOOGLE_ID ??
            process.env.GOOGLE_CLIENT_ID ??
            process.env.GOOGLE_ID,
        clientSecret:
            process.env.AUTH_GOOGLE_SECRET ??
            process.env.GOOGLE_CLIENT_SECRET ??
            process.env.GOOGLE_SECRET,
    };
}

export function appleProviderConfig() {
    return {
        clientId:
            process.env.AUTH_APPLE_ID ??
            process.env.APPLE_CLIENT_ID ??
            process.env.APPLE_ID,
        clientSecret:
            process.env.AUTH_APPLE_SECRET ??
            process.env.APPLE_CLIENT_SECRET ??
            process.env.APPLE_SECRET,
    };
}
