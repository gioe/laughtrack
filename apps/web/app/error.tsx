"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import ErrorPage from "@/ui/components/errorPage";

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        Sentry.captureException(error, { extra: { digest: error.digest } });
    }, [error]);

    return (
        <ErrorPage
            title="Something went wrong"
            description="An unexpected error occurred. You can try again or head back to the home page."
            reset={reset}
        />
    );
}
