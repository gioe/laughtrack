import * as Sentry from "@sentry/nextjs";

export async function register() {
    if (process.env.NEXT_RUNTIME === "nodejs") {
        const { validateWebStartupEnv } = await import("@/lib/env/startup");
        validateWebStartupEnv();

        Sentry.init({
            dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
            environment: process.env.NODE_ENV,
            tracesSampleRate: 0.1,
            enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
        });
    }

    if (process.env.NEXT_RUNTIME === "edge") {
        Sentry.init({
            dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
            environment: process.env.NODE_ENV,
            tracesSampleRate: 0.1,
            enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
        });
    }
}

export const onRequestError = Sentry.captureRequestError;
