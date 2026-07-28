"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Bookmark, Loader2, Ticket } from "lucide-react";
import { formatShowCountdown } from "@/util/dateUtil";
import { showHeroImage } from "@/util/show/showHeroImage";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import MarqueeHero from "@/ui/pages/entity/MarqueeHero";
import { Button } from "@/ui/components/ui/button";
import { useSavedShow } from "@/hooks/useSavedShow";

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
    // Prefer the inferred headliner's headshot over the club image, matching
    // the iOS marquee (ShowDetailPresentation.heroImageURL).
    const hero = showHeroImage(show);
    const imageSrc = hero.src && hero.src !== PLACEHOLDER ? hero.src : null;
    const imageAlt = hero.headliner?.name ?? show.clubName ?? "Club";
    const {
        isSaved,
        isAuthenticated,
        isLoading,
        isPending,
        error,
        announcement,
        toggleSavedShow,
    } = useSavedShow(show.id);
    const savedShowLabel = !isAuthenticated
        ? "Sign in to save this show"
        : isLoading
          ? "Checking saved show status"
          : isPending
            ? isSaved
                ? "Removing saved show…"
                : "Saving show…"
            : isSaved
              ? "Remove saved show"
              : "Save show";

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
            imageAlt={imageAlt}
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

            <div className="mt-2 flex flex-col items-center gap-2">
                <Button
                    type="button"
                    variant="roundedShimmerOutline"
                    size="roundedShimmerOutline"
                    onClick={() => void toggleSavedShow()}
                    disabled={isLoading || isPending}
                    aria-label={savedShowLabel}
                    aria-pressed={
                        isAuthenticated && !isLoading ? isSaved : undefined
                    }
                    aria-busy={isLoading || isPending || undefined}
                    className={
                        isSaved
                            ? "border-highlight bg-highlight text-foreground hover:bg-highlight/85 hover:text-foreground"
                            : undefined
                    }
                >
                    {isLoading || isPending ? (
                        <Loader2
                            className="mr-2 h-4 w-4 animate-spin"
                            aria-hidden="true"
                        />
                    ) : (
                        <Bookmark
                            className={`mr-2 h-4 w-4 ${
                                isSaved ? "fill-current" : ""
                            }`}
                            aria-hidden="true"
                        />
                    )}
                    {savedShowLabel}
                </Button>

                {announcement ? (
                    <p className="sr-only" role="status" aria-live="polite">
                        {announcement}
                    </p>
                ) : null}
                {error ? (
                    <p
                        className="max-w-sm text-sm font-medium text-red-200"
                        role="alert"
                    >
                        {error}
                    </p>
                ) : null}
            </div>

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
