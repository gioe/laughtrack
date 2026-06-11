"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Ticket } from "lucide-react";
import { formatShowCountdown } from "@/util/dateUtil";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import MarqueeHero from "@/ui/pages/entity/MarqueeHero";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ShowDetailHeaderProps {
    show: ShowDetailDTO;
    isAdmin?: boolean;
}

// Badge classes per countdown tone — kept literal so the JIT picks them up.
// Mirrors the iOS LaughTrackBadge tone recipes (LaughTrackComponents.swift):
// live → accent (accent-strong text on accent-muted wash), future → highlight
// (warm brown), past → neutral (canvas surface). Each tone owns its text and
// border color, so the span carries no color classes of its own.
const COUNTDOWN_TONE_CLASSES: Record<string, string> = {
    future: "bg-highlight/85 text-foreground border border-strong/50",
    live: "bg-accent-muted/45 text-accent-strong border border-accent-strong/35",
    past: "bg-canvas text-foreground border border-subtle",
};

const ShowDetailHeader: React.FC<ShowDetailHeaderProps> = ({
    show,
    isAdmin = false,
}) => {
    // Re-derive the countdown every minute so future→live→past transitions
    // fire without a page reload (a user who lands 4 minutes before showtime
    // otherwise sees the label frozen as the show starts).
    const [now, setNow] = useState<Date>(() => new Date());
    useEffect(() => {
        const interval = setInterval(() => setNow(new Date()), 60_000);
        return () => clearInterval(interval);
    }, []);
    const heading =
        show.name && show.name.trim()
            ? show.name
            : `Comedy at ${show.clubName ?? ""}`;
    const countdown = formatShowCountdown(show.date.toString(), now);
    const imageSrc =
        show.imageUrl && show.imageUrl !== PLACEHOLDER ? show.imageUrl : null;

    return (
        <MarqueeHero
            title={heading}
            eyebrow={
                show.clubName ? (
                    <Link
                        href={`/club/${show.clubName}`}
                        className="text-caption font-semibold uppercase tracking-[0.2em] text-accent-strong font-dmSans underline-offset-4 hover:underline focus-visible:underline"
                    >
                        {show.clubName}
                    </Link>
                ) : null
            }
            imageSrc={imageSrc}
            imageAlt={show.clubName ?? "Club"}
            fallback={
                <div className="flex h-full w-full items-center justify-center bg-surface-muted">
                    <Ticket
                        size={64}
                        className="text-accent-strong"
                        aria-hidden="true"
                    />
                </div>
            }
        >
            <span
                className={`inline-block text-caption font-bold uppercase tracking-wider px-2.5 py-1 rounded-full font-dmSans ${COUNTDOWN_TONE_CLASSES[countdown.tone]}`}
                aria-live={countdown.tone === "live" ? "polite" : "off"}
            >
                {countdown.label}
            </span>

            {/* Admin-only debug affordance — re-homed from the removed
                date/room/address block (the ticket stub owns that data now). */}
            {isAdmin && (
                <p
                    className="mt-2 inline-block text-xs font-mono text-gray-600 bg-stone-200 px-2 py-0.5 rounded"
                    data-testid="show-detail-admin-id"
                >
                    Show ID: {show.id}
                </p>
            )}
        </MarqueeHero>
    );
};

export default ShowDetailHeader;
