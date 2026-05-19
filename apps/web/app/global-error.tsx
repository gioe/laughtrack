"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import Link from "next/link";

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
                        background: "#fafaf0",
                        color: "#361E14",
                    }}
                >
                    <h1
                        style={{
                            fontSize: "2rem",
                            fontWeight: "bold",
                            color: "#361E14",
                        }}
                    >
                        Something went wrong
                    </h1>
                    <p style={{ color: "#4A4A4A", maxWidth: "28rem" }}>
                        An unexpected error occurred. You can try again or head
                        back to the home page.
                    </p>
                    <div style={{ display: "flex", gap: "16px" }}>
                        <button
                            onClick={reset}
                            style={{
                                padding: "8px 20px",
                                background: "#7A3F16",
                                color: "#fff",
                                borderRadius: "6px",
                                border: "none",
                                cursor: "pointer",
                            }}
                        >
                            Try again
                        </button>
                        <Link
                            href="/"
                            style={{
                                padding: "8px 20px",
                                background: "transparent",
                                color: "#7A3F16",
                                borderRadius: "6px",
                                border: "2px solid #7A3F16",
                                textDecoration: "none",
                            }}
                        >
                            Go home
                        </Link>
                    </div>
                </div>
            </body>
        </html>
    );
}
