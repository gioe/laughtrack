"use client";

import { Check, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "laughtrack.adult-content-acknowledged";
const COOKIE_KEY = "laughtrack_adult_content_acknowledged";
const ACKNOWLEDGED_VALUE = "true";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function hasAcknowledgedAdultContent(): boolean {
    if (window.localStorage.getItem(STORAGE_KEY) === ACKNOWLEDGED_VALUE) {
        return true;
    }

    return document.cookie
        .split(";")
        .map((cookie) => cookie.trim())
        .includes(`${COOKIE_KEY}=${ACKNOWLEDGED_VALUE}`);
}

function persistAcknowledgment() {
    window.localStorage.setItem(STORAGE_KEY, ACKNOWLEDGED_VALUE);
    document.cookie = `${COOKIE_KEY}=${ACKNOWLEDGED_VALUE};path=/;max-age=${COOKIE_MAX_AGE_SECONDS};SameSite=Lax`;
}

export default function AdultContentAcknowledgment() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        setIsVisible(!hasAcknowledgedAdultContent());
    }, []);

    if (!isVisible) return null;

    const acknowledge = () => {
        persistAcknowledgment();
        setIsVisible(false);
    };

    return (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm">
            <section
                role="dialog"
                aria-modal="true"
                aria-labelledby="adult-content-acknowledgment-title"
                className="w-full max-w-md rounded-lg border border-white/10 bg-coconut-cream p-5 shadow-2xl sm:p-6"
            >
                <div className="flex items-start gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-copper/20 text-copper">
                        <ShieldAlert aria-hidden="true" size={22} />
                    </span>
                    <div className="min-w-0">
                        <h2
                            id="adult-content-acknowledgment-title"
                            className="font-gilroy-bold text-h3 leading-tight text-white"
                        >
                            Adult content notice
                        </h2>
                        <p className="mt-3 font-dmSans text-body leading-6 text-white/80">
                            This app shows live comedy events that may contain
                            adult content, including mature language and themes.
                        </p>
                    </div>
                </div>

                <button
                    type="button"
                    onClick={acknowledge}
                    className="mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-copper px-4 py-2 font-dmSans text-body font-semibold text-white transition hover:bg-copper-bright focus:outline-none focus:ring-2 focus:ring-copper focus:ring-offset-2 focus:ring-offset-coconut-cream"
                >
                    <Check aria-hidden="true" size={18} />
                    I understand
                </button>
            </section>
        </div>
    );
}
