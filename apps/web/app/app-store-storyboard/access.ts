export function isLocalDevelopment() {
    const vercelEnvironment = process.env.VERCEL_ENV;

    return (
        process.env.NODE_ENV === "development" &&
        (vercelEnvironment === undefined || vercelEnvironment === "development")
    );
}
