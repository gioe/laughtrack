"use client";

import { useState, useCallback } from "react";

export type GeolocationStatus = "idle" | "loading" | "success" | "error";

export type GeolocationError = "denied" | "timeout" | "unavailable" | "no_zip";

interface UseGeolocationResult {
    status: GeolocationStatus;
    error: GeolocationError | null;
    requestLocation: () => void;
}

const ZIP_STORAGE_KEY = "laughtrack_zip";

export function useGeolocation(
    onSuccess: (zip: string) => void,
): UseGeolocationResult {
    const [status, setStatus] = useState<GeolocationStatus>("idle");
    const [error, setError] = useState<GeolocationError | null>(null);

    const requestLocation = useCallback(() => {
        if (!navigator.geolocation) {
            setStatus("error");
            setError("unavailable");
            return;
        }

        setStatus("loading");
        setError(null);

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                try {
                    const res = await fetch(
                        `/api/geocode?lat=${pos.coords.latitude}&lng=${pos.coords.longitude}`,
                    );
                    if (!res.ok) {
                        setStatus("error");
                        setError("no_zip");
                        return;
                    }
                    const data = await res.json();
                    const zip: string | null = data?.zip ?? null;
                    if (zip) {
                        if (typeof window !== "undefined") {
                            localStorage.setItem(ZIP_STORAGE_KEY, zip);
                        }
                        setStatus("success");
                        setError(null);
                        onSuccess(zip);
                    } else {
                        setStatus("error");
                        setError("no_zip");
                    }
                } catch {
                    setStatus("error");
                    setError("no_zip");
                }
            },
            (err) => {
                setStatus("error");
                if (err.code === GeolocationPositionError.PERMISSION_DENIED) {
                    setError("denied");
                } else if (err.code === GeolocationPositionError.TIMEOUT) {
                    setError("timeout");
                } else {
                    setError("unavailable");
                }
            },
            { timeout: 10000 },
        );
    }, [onSuccess]);

    return { status, error, requestLocation };
}
