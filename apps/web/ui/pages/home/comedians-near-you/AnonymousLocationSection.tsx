"use client";

import { useState, useCallback } from "react";
import ComedianNearYouSection from "@/ui/pages/home/comedians-near-you";
import { getComediansByZipAction } from "@/app/actions/getComediansByZipAction";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { removeNonNumbers } from "@/util/primatives/stringUtil";

type Step = "prompt" | "loading" | "zip-entry" | "loaded" | "declined";

async function reverseGeocodeToZip(
    lat: number,
    lng: number,
): Promise<string | null> {
    try {
        const res = await fetch(`/api/geocode?lat=${lat}&lng=${lng}`);
        if (!res.ok) return null;
        const data = await res.json();
        return data?.zip ?? null;
    } catch {
        return null;
    }
}

const DISMISSED_KEY = "laughtrack_location_dismissed";

export default function AnonymousLocationSection() {
    const [step, setStep] = useState<Step>(() => {
        if (
            typeof window !== "undefined" &&
            localStorage.getItem(DISMISSED_KEY) === "1"
        ) {
            return "declined";
        }
        return "prompt";
    });
    const [comedians, setComedians] = useState<ComedianDTO[]>([]);
    const [zipCode, setZipCode] = useState("");
    const [zipInput, setZipInput] = useState("");
    const [error, setError] = useState<string | null>(null);

    const fetchComedians = useCallback(async (zip: string) => {
        setStep("loading");
        setError(null);
        const result = await getComediansByZipAction(zip);
        if (result.length > 0) {
            setComedians(result);
            setZipCode(zip);
            setStep("loaded");
        } else {
            setError("No comedians found near that location.");
            setStep("zip-entry");
        }
    }, []);

    const handleGeolocate = useCallback(() => {
        if (!navigator.geolocation) {
            setStep("zip-entry");
            return;
        }
        setStep("loading");
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const zip = await reverseGeocodeToZip(
                    pos.coords.latitude,
                    pos.coords.longitude,
                );
                if (zip) {
                    await fetchComedians(zip);
                } else {
                    setError(
                        "Could not determine zip code from your location.",
                    );
                    setStep("zip-entry");
                }
            },
            () => {
                setStep("zip-entry");
            },
            { timeout: 10000 },
        );
    }, [fetchComedians]);

    const handleZipSubmit = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            const trimmed = zipInput.trim();
            if (!/^\d{5}$/.test(trimmed)) {
                setError("Please enter a valid 5-digit zip code.");
                return;
            }
            await fetchComedians(trimmed);
        },
        [zipInput, fetchComedians],
    );

    if (step === "declined") return null;

    if (step === "loaded") {
        return (
            <ComedianNearYouSection comedians={comedians} zipCode={zipCode} />
        );
    }

    return (
        <div className="max-w-7xl w-full mx-auto py-16 px-4 sm:px-6">
            <div className="text-center mb-8 animate-fadeIn">
                <h2 className="text-4xl sm:text-5xl font-bold font-gilroy-bold mb-4 text-cedar">
                    Comedians Near You
                </h2>
                <p className="text-gray-600 font-dmSans text-lg sm:text-xl max-w-2xl mx-auto">
                    Find comedians performing in your area.
                </p>
            </div>

            {step === "loading" ? (
                <div
                    className="flex justify-center py-8"
                    aria-label="Loading comedians"
                    role="status"
                >
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-cedar" />
                    <span className="sr-only">
                        Loading comedians near you...
                    </span>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-6 max-w-sm mx-auto">
                    {step === "prompt" && (
                        <button
                            onClick={handleGeolocate}
                            className="w-full bg-[#2D1810] text-white px-8 py-4 rounded-full
                            transform transition-all duration-300 ease-in-out
                            hover:scale-105 hover:shadow-lg hover:bg-copper
                            active:scale-95 font-dmSans text-lg"
                        >
                            Use My Location
                        </button>
                    )}

                    <div className="flex items-center w-full gap-3">
                        <div className="flex-1 border-t border-gray-300" />
                        <span className="text-gray-400 font-dmSans text-sm">
                            {step === "prompt" ? "or" : "Enter your zip code"}
                        </span>
                        <div className="flex-1 border-t border-gray-300" />
                    </div>

                    <form
                        onSubmit={handleZipSubmit}
                        className="flex gap-2 w-full"
                    >
                        <input
                            type="text"
                            inputMode="numeric"
                            pattern="[0-9]*"
                            value={zipInput}
                            onChange={(e) =>
                                setZipInput(removeNonNumbers(e.target.value))
                            }
                            placeholder="Enter zip code"
                            maxLength={5}
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-full
                            font-dmSans text-base focus:outline-none focus:border-cedar"
                        />
                        <button
                            type="submit"
                            className="bg-[#2D1810] text-white px-6 py-3 rounded-full
                            transform transition-all duration-300 ease-in-out
                            hover:scale-105 hover:shadow-lg hover:bg-copper
                            active:scale-95 font-dmSans"
                        >
                            Go
                        </button>
                    </form>

                    {error && (
                        <p className="text-red-500 font-dmSans text-sm">
                            {error}
                        </p>
                    )}

                    <button
                        onClick={() => {
                            localStorage.setItem(DISMISSED_KEY, "1");
                            setStep("declined");
                        }}
                        className="text-gray-400 font-dmSans text-sm hover:text-gray-600 transition-colors"
                    >
                        No thanks
                    </button>
                </div>
            )}
        </div>
    );
}
