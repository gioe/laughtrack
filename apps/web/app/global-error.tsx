"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
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
        <html>
            <body>
                <div
                    style={{
                        minHeight: "100vh",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "24px",
                        padding: "16px",
                        textAlign: "center",
                    }}
                >
                    <h1
                        style={{
                            fontSize: "2rem",
                            fontWeight: "bold",
                            color: "#1f2937",
                        }}
                    >
                        Something went wrong
                    </h1>
                    <p style={{ color: "#6b7280", maxWidth: "28rem" }}>
                        An unexpected error occurred. You can try again or head
                        back to the home page.
                    </p>
                    <div style={{ display: "flex", gap: "16px" }}>
                        <button
                            onClick={reset}
                            style={{
                                padding: "8px 20px",
                                background: "#3b82f6",
                                color: "#fff",
                                borderRadius: "6px",
                                border: "none",
                                cursor: "pointer",
                            }}
                        >
                            Try again
                        </button>
                        <a
                            href="/"
                            style={{
                                padding: "8px 20px",
                                background: "transparent",
                                color: "#374151",
                                borderRadius: "6px",
                                border: "1px solid #d1d5db",
                                textDecoration: "none",
                            }}
                        >
                            Go home
                        </a>
                    </div>
                </div>
            </body>
        </html>
    );
}
