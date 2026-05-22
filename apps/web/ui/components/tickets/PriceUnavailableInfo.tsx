"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { Modal } from "@/ui/components/modals/basic";

export const PRICE_UNAVAILABLE_COPY =
    "The venue has not made this ticket price available yet. Use Get Tickets to check current pricing on the venue's ticketing page.";

interface PriceUnavailableInfoProps {
    className?: string;
}

const PriceUnavailableInfo = ({ className }: PriceUnavailableInfoProps) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <button
                type="button"
                aria-label="Why is the price unavailable?"
                className={`inline-flex h-8 w-8 items-center justify-center rounded-full border border-copper/25 bg-white/85 text-copper shadow-sm transition hover:bg-coconut-cream focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper ${className ?? ""}`}
                onClick={() => setIsOpen(true)}
            >
                <Info size={16} aria-hidden="true" />
            </button>
            <Modal
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                title="Price unavailable"
            >
                <p className="font-dmSans text-sm leading-6 text-gray-700">
                    {PRICE_UNAVAILABLE_COPY}
                </p>
            </Modal>
        </>
    );
};

export default PriceUnavailableInfo;
