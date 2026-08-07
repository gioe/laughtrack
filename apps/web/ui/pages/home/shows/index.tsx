"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";
import ScrollButtons from "@/ui/components/scroll";
import SectionHeader from "@/ui/components/sectionHeader";
import {
    RAIL_CARD_COMPACT_WIDTH_PX,
    RAIL_CARD_STANDARD_WIDTH_PX,
    RAIL_CARD_GAP_PX,
    RAIL_CARD_STANDARD_MIN_VIEWPORT_PX,
} from "@/util/constants/railCardConstants";
import DiscoveryImpressionTracker, {
    type DiscoveryPresentation,
} from "./DiscoveryImpressionTracker";

interface ShowDiscoverySectionProps {
    // Copper uppercase kicker above the title, mirroring the iOS home-rail
    // vocabulary (e.g. "Favorites", "This week"). Omit on rails where iOS
    // renders no eyebrow either.
    eyebrow?: string;
    title: string;
    subtitle: string;
    shows: ShowDTO[];
    seeAllHref: string;
    // Optional stable identifier for visual regression tests. When omitted,
    // falls back to a slug derived from `title` — but callers that pin
    // baselines (e.g. apps/web/app/page.fixture.tsx) should pass an explicit
    // value so a copy tweak to `title` doesn't silently break the locator.
    testId?: string;
    discoveryPresentation?: DiscoveryPresentation;
    /** Structured server reason copy keyed by show identity. */
    reasonLabels?: Readonly<Record<number, string>>;
}

const ShowDiscoverySection = ({
    eyebrow,
    title,
    subtitle,
    shows,
    seeAllHref,
    testId,
    discoveryPresentation,
    reasonLabels,
}: ShowDiscoverySectionProps) => {
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [isClient, setIsClient] = useState(false);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(true);

    useEffect(() => {
        setIsClient(true);
    }, []);

    const checkScrollability = useCallback(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const scrollPosition = Math.round(container.scrollLeft);
        const maxScroll = container.scrollWidth - container.clientWidth;
        setCanScrollLeft(scrollPosition > 2);
        setCanScrollRight(
            Math.ceil(scrollPosition) < Math.floor(maxScroll - 10),
        );
    }, []);

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const handleScroll = () => requestAnimationFrame(checkScrollability);
        checkScrollability();
        setTimeout(checkScrollability, 100);
        container.addEventListener("scroll", handleScroll);
        window.addEventListener("resize", handleScroll);
        return () => {
            container.removeEventListener("scroll", handleScroll);
            window.removeEventListener("resize", handleScroll);
        };
    }, [isClient, checkScrollability]);

    const scroll = (direction: "left" | "right") => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const cardWidth =
            window.innerWidth >= RAIL_CARD_STANDARD_MIN_VIEWPORT_PX
                ? RAIL_CARD_STANDARD_WIDTH_PX + RAIL_CARD_GAP_PX
                : RAIL_CARD_COMPACT_WIDTH_PX + RAIL_CARD_GAP_PX;
        const scrollAmount = cardWidth * 3;
        const currentScroll = container.scrollLeft;
        const maxScroll = container.scrollWidth - container.clientWidth;
        let targetScroll: number;
        if (direction === "left") {
            const currentSet = Math.ceil(currentScroll / scrollAmount);
            targetScroll = Math.max(0, currentSet - 1) * scrollAmount;
        } else {
            targetScroll = Math.min(currentScroll + scrollAmount, maxScroll);
        }
        container.scrollTo({ left: targetScroll, behavior: "smooth" });
        setTimeout(checkScrollability, 300);
    };

    const resolvedTestId =
        testId ??
        `shows-section-${title
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, "")}`;

    return (
        <div
            data-testid={resolvedTestId}
            className="max-w-7xl w-full mx-auto py-12 px-4 sm:px-6 lg:px-8"
        >
            <div className="flex flex-col sm:flex-row md:flex-row lg:flex-row justify-between items-start sm:items-center md:items-center lg:items-center mb-6">
                <SectionHeader
                    eyebrow={eyebrow}
                    title={title}
                    subtitle={subtitle}
                    className="mb-4 sm:mb-0"
                />
                <div className="flex items-center gap-4 self-end sm:self-auto md:self-auto lg:self-auto">
                    <Link
                        href={seeAllHref}
                        aria-label={`See all ${title} shows`}
                        className="text-sm font-dmSans text-copper hover:underline whitespace-nowrap"
                    >
                        See all →
                    </Link>
                    <ScrollButtons
                        leftOnClick={() => scroll("left")}
                        rightOnClick={() => scroll("right")}
                        leftDisabled={!canScrollLeft}
                        rightDisabled={!canScrollRight}
                    />
                </div>
            </div>

            <div
                ref={scrollContainerRef}
                className="flex gap-4 overflow-x-auto scrollbar-hide py-4 px-2 scroll-smooth"
                style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
            >
                {shows.map((show, index) => {
                    const cardClassName =
                        "relative flex-none w-rail-card-compact sm:w-rail-card-standard md:w-rail-card-standard lg:w-rail-card-standard max-w-[calc(100vw-2rem)]";
                    const reasonLabel = reasonLabels?.[show.id];
                    const card = (discoveryAttribution?: {
                        impressionId?: string;
                        onShowDetail: () => void;
                    }) => (
                        <>
                            {reasonLabel ? (
                                <p className="relative z-[3] mb-2 w-fit rounded-full border border-copper/30 bg-cedar px-3 py-1 font-dmSans text-caption font-semibold text-champagne">
                                    {reasonLabel}
                                </p>
                            ) : null}
                            <ShowCard
                                show={show}
                                density="compact"
                                discoveryAttribution={discoveryAttribution}
                            />
                        </>
                    );
                    if (!discoveryPresentation) {
                        return (
                            <div key={show.id} className={cardClassName}>
                                {card()}
                            </div>
                        );
                    }
                    const presentationKey = [
                        show.id,
                        discoveryPresentation.surface,
                        discoveryPresentation.policyVersion,
                    ].join(":");
                    return (
                        <DiscoveryImpressionTracker
                            key={presentationKey}
                            showId={show.id}
                            rank={index + 1}
                            className={cardClassName}
                            {...discoveryPresentation}
                        >
                            {(attribution) => card(attribution)}
                        </DiscoveryImpressionTracker>
                    );
                })}
            </div>
        </div>
    );
};

export default ShowDiscoverySection;
