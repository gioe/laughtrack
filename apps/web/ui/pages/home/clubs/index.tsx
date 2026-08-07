"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { ClubDTO } from "@/objects/class/club/club.interface";
import PopularClubCard from "@/ui/components/cards/club/popular";
import ScrollButtons from "@/ui/components/scroll";
import SectionHeader from "@/ui/components/sectionHeader";
import {
    RAIL_CARD_COMPACT_WIDTH_PX,
    RAIL_CARD_STANDARD_WIDTH_PX,
    RAIL_CARD_GAP_PX,
    RAIL_CARD_STANDARD_MIN_VIEWPORT_PX,
} from "@/util/constants/railCardConstants";

interface TrendingClubsCarouselProps {
    clubs: ClubDTO[];
    // When set, the rail is scoped to the viewer's area and titled accordingly.
    // Omitted (no resolved location) falls back to the global popular list.
    zipCode?: string;
    /** Preserve the authoritative order supplied by a server-directed plan. */
    preserveOrder?: boolean;
}

const TrendingClubsCarousel = ({
    clubs,
    zipCode,
    preserveOrder = false,
}: TrendingClubsCarouselProps) => {
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [isClient, setIsClient] = useState(false);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(true);
    const [activeIndicator, setActiveIndicator] = useState(0);

    // Sort clubs once instead of on every render
    const sortedClubs = React.useMemo(() => {
        if (preserveOrder) return clubs;
        return [...clubs].sort((a, b) =>
            (a.activeComedianCount ?? 0) > (b.activeComedianCount ?? 0)
                ? -1
                : 1,
        );
    }, [clubs, preserveOrder]);

    useEffect(() => {
        setIsClient(true);
    }, []);

    const checkScrollability = useCallback(() => {
        const container = scrollContainerRef.current;
        if (!container) return;

        // Get actual card width including gap
        const cardWidth =
            window.innerWidth >= RAIL_CARD_STANDARD_MIN_VIEWPORT_PX
                ? RAIL_CARD_STANDARD_WIDTH_PX + RAIL_CARD_GAP_PX
                : RAIL_CARD_COMPACT_WIDTH_PX + RAIL_CARD_GAP_PX;
        const scrollPosition = Math.round(container.scrollLeft);
        const maxScroll = container.scrollWidth - container.clientWidth;

        // More lenient scroll position checks for buttons
        setCanScrollLeft(scrollPosition > 2);
        setCanScrollRight(
            Math.ceil(scrollPosition) < Math.floor(maxScroll - 10),
        );

        // Calculate active indicator based on actual card width
        if (sortedClubs.length > 0) {
            const totalSets = Math.ceil(sortedClubs.length / 3);

            if (Math.abs(scrollPosition - maxScroll) < 20) {
                // If we're very close to the end, show the last indicator
                setActiveIndicator(totalSets - 1);
            } else {
                const currentCard = Math.round(scrollPosition / cardWidth);
                const newActiveIndicator = Math.min(
                    Math.floor(currentCard / 3),
                    totalSets - 1,
                );
                setActiveIndicator(newActiveIndicator);
            }
        }
    }, [sortedClubs.length]);

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;

        const handleScroll = () => {
            requestAnimationFrame(checkScrollability);
        };

        // Initial check after content loads
        const initialCheck = () => {
            checkScrollability();
            // Check again after a short delay to account for any layout shifts
            setTimeout(checkScrollability, 100);
        };
        initialCheck();

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

        // Use actual card width
        const cardWidth =
            window.innerWidth >= RAIL_CARD_STANDARD_MIN_VIEWPORT_PX
                ? RAIL_CARD_STANDARD_WIDTH_PX + RAIL_CARD_GAP_PX
                : RAIL_CARD_COMPACT_WIDTH_PX + RAIL_CARD_GAP_PX;
        const visibleCards = 3;
        const scrollAmount = cardWidth * visibleCards;

        const currentScroll = container.scrollLeft;
        const maxScroll = container.scrollWidth - container.clientWidth;

        let targetScroll;
        if (direction === "left") {
            // Calculate the nearest previous card set
            const currentSet = Math.ceil(currentScroll / scrollAmount);
            const targetSet = Math.max(0, currentSet - 1);
            targetScroll = targetSet * scrollAmount;
        } else {
            // For right scroll, try to show new cards if possible
            targetScroll = currentScroll + scrollAmount;
            if (targetScroll > maxScroll) {
                targetScroll = maxScroll;
            }
        }

        container.scrollTo({
            left: targetScroll,
            behavior: "smooth",
        });

        // Update scroll state after animation
        setTimeout(checkScrollability, 300);
    };

    const scrollToIndicator = (index: number) => {
        const container = scrollContainerRef.current;
        if (!container) return;

        const cardWidth =
            window.innerWidth >= RAIL_CARD_STANDARD_MIN_VIEWPORT_PX
                ? RAIL_CARD_STANDARD_WIDTH_PX + RAIL_CARD_GAP_PX
                : RAIL_CARD_COMPACT_WIDTH_PX + RAIL_CARD_GAP_PX;
        const targetScroll = index * (cardWidth * 3);

        container.scrollTo({
            left: Math.min(
                targetScroll,
                container.scrollWidth - container.clientWidth,
            ),
            behavior: "smooth",
        });

        // Update scroll state after animation
        setTimeout(checkScrollability, 300);
    };

    return (
        <div className="max-w-7xl w-full mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row md:flex-row lg:flex-row justify-between items-start sm:items-center md:items-center lg:items-center mb-6">
                {/* No eyebrow: the iOS popular-clubs rail renders no header
                    eyebrow, so web stays in lockstep (TASK-2751). */}
                <SectionHeader
                    title={zipCode ? "Popular clubs near you" : "Popular clubs"}
                    subtitle={
                        zipCode
                            ? `The most active comedy venues near ${zipCode} right now.`
                            : "Check out our most popular comedy venues"
                    }
                    className="mb-4 sm:mb-0"
                />
                <div className="flex gap-2 self-end sm:self-auto md:self-auto lg:self-auto">
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
                {sortedClubs.map((dto) => (
                    <div
                        key={dto.id ?? dto.name}
                        className="flex-none w-rail-card-compact sm:w-rail-card-standard md:w-rail-card-standard lg:w-rail-card-standard max-w-[calc(100vw-2rem)]"
                    >
                        <PopularClubCard entity={dto} />
                    </div>
                ))}
            </div>

            <div className="flex justify-center mt-4 gap-1.5 sm:hidden md:hidden lg:hidden">
                {Array.from({ length: Math.ceil(sortedClubs.length / 3) }).map(
                    (_, index) => (
                        <button
                            key={`indicator-${index}`}
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                                index === activeIndicator
                                    ? "w-8 bg-cedar"
                                    : "w-2 bg-white/25"
                            }`}
                            onClick={() => scrollToIndicator(index)}
                            aria-label={`Go to slide set ${index + 1}`}
                        />
                    ),
                )}
            </div>
        </div>
    );
};

export default TrendingClubsCarousel;
