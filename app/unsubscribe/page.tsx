"use client";

import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function UnsubscribePage() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");
    const [status, setStatus] = useState<"loading" | "success" | "error">(
        "loading",
    );
    const [message, setMessage] = useState("Processing your request...");

    useEffect(() => {
        if (!token) {
            setStatus("error");
            setMessage("Invalid unsubscribe link");
            return;
        }

        const processUnsubscribe = async () => {
            try {
                const response = await fetch("/api/unsubscribe", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ token }),
                });

                if (!response.ok) {
                    throw new Error("Failed to unsubscribe");
                }

                setStatus("success");
                setMessage(
                    "You have been successfully unsubscribed notifications",
                );
            } catch (error) {
                setStatus("error");
                setMessage(
                    "Something went wrong. Please try again or contact support.",
                );
            }
        };

        processUnsubscribe();
    }, [token]);

    return (
        <div className="min-h-screen bg-ivory flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-ivory rounded-lg shadow-md p-8">
                <h1 className="text-2xl font-bold text-center mb-6">
                    Unsubscribe from Notifications
                </h1>

                <div className="text-center">
                    {status === "loading" && (
                        <div className="animate-pulse font-gilroy-bold text-[32px] font-bold">
                            <p>{message}</p>
                        </div>
                    )}

                    {status === "success" && (
                        <div className="text-copper">
                            <p>{message}</p>
                            <div className="pt-3">
                                <FullRoundedButton
                                    handleClick={() =>
                                        (window.location.href = "/")
                                    }
                                    label="Return to Homepage"
                                />
                            </div>
                        </div>
                    )}

                    {status === "error" && (
                        <div className="text-red-600">
                            <p>{message}</p>
                            <p className="mt-2 text-sm">
                                Need help?{" "}
                                <a href="/contact" className="underline">
                                    Contact support
                                </a>
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
