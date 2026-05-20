export async function register() {
    if (process.env.NEXT_RUNTIME !== "edge") {
        const { validateWebStartupEnv } = await import("@/lib/env/startup");
        validateWebStartupEnv();
    }
}
