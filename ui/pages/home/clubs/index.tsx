"use client";

import React, { useState, useRef, useEffect } from "react";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import PopularClubCard from "@/ui/components/cards/club/popular";
import ScrollButtons from "@/ui/components/scroll";

interface TrendingClubsCarouselProps {
    clubs: ClubDTO[];
}

const TrendingClubsCarousel = ({ clubs }: TrendingClubsCarouselProps) => {
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [isClient, setIsClient] = useState(false);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(true);
    const [activeIndicator, setActiveIndicator] = useState(0);

    // Sort clubs once instead of on every render
    const sortedClubs = React.useMemo(() => {
        return [...clubs].sort((a, b) =>
            (a.active_comedian_count ?? 0) > (b.active_comedian_count ?? 0)
                ? -1
                : 1,
        );
    }, [clubs]);

    useEffect(() => {
        setIsClient(true);
    }, []);

    // Check if scrolling is possible in either direction and update indicators
    const checkScrollability = () => {
        const container = scrollContainerRef.current;
        if (!container) return;

        // Check if can scroll left (scrollLeft > 0)
        // Use a small threshold (1px) to account for rounding errors and browser inconsistencies
        setCanScrollLeft(container.scrollLeft > 1);

        // Check if can scroll right (scrollLeft + clientWidth < scrollWidth)
        setCanScrollRight(
            Math.ceil(container.scrollLeft + container.clientWidth) <
                container.scrollWidth - 10,
        );

        // Update the active indicator based on scroll position
        if (sortedClubs.length > 0) {
            const totalIndicators = Math.ceil(sortedClubs.length / 3);
            const scrollPercentage =
                container.scrollLeft /
                (container.scrollWidth - container.clientWidth);

            // Calculate which indicator should be active
            const newActiveIndicator = Math.min(
                Math.floor(scrollPercentage * totalIndicators),
                totalIndicators - 1,
            );

            setActiveIndicator(newActiveIndicator);
        }
    };

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;

        // Define a handler that uses a timeout to ensure values are settled
        const handleScroll = () => {
            // Use requestAnimationFrame for better performance and to ensure DOM is updated
            requestAnimationFrame(() => {
                checkScrollability();

                // Debug log (remove in production)
                console.log(
                    "Scroll position:",
                    container.scrollLeft,
                    "Can scroll left:",
                    container.scrollLeft > 1,
                );
            });
        };

        // Initial check - use a timeout to ensure the DOM has fully rendered
        setTimeout(checkScrollability, 100);

        // Add scroll event listener with debounce-like behavior
        container.addEventListener("scroll", handleScroll);

        // Add resize listener since card sizes might change on window resize
        window.addEventListener("resize", handleScroll);

        return () => {
            container.removeEventListener("scroll", handleScroll);
            window.removeEventListener("resize", handleScroll);
        };
    }, [isClient, sortedClubs.length]);

    const scroll = (direction: "left" | "right") => {
        const container = scrollContainerRef.current;
        if (!container) {
            console.warn("Scroll container ref is not available");
            return;
        }

        try {
            // Scroll by the width of visible cards (approximately)
            const cardWidth = 300; // Approximate width of a card with margin
            const visibleWidth = container.clientWidth;

            // Scroll by the number of fully visible cards, or at least one card
            const scrollAmount =
                direction === "left"
                    ? -Math.max(visibleWidth * 0.8, cardWidth)
                    : Math.max(visibleWidth * 0.8, cardWidth);

            // Calculate target scroll position
            let targetScrollLeft = container.scrollLeft + scrollAmount;

            // Handle edge cases
            if (direction === "left") {
                // If scrolling left, don't go beyond the start (with small buffer)
                targetScrollLeft = Math.max(0, targetScrollLeft);

                // If we're close to the start, go all the way to start
                if (targetScrollLeft < 50) {
                    targetScrollLeft = 0;
                }
            } else {
                // If scrolling right, don't go beyond the end (with small buffer)
                const maxScroll = container.scrollWidth - container.clientWidth;
                targetScrollLeft = Math.min(maxScroll, targetScrollLeft);

                // If we're close to the end, go all the way to end
                if (maxScroll - targetScrollLeft < 50) {
                    targetScrollLeft = maxScroll;
                }
            }

            // Perform the scroll
            container.scrollTo({
                left: targetScrollLeft,
                behavior: "smooth",
            });

            // Force update the scroll state after animation completes
            setTimeout(checkScrollability, 500);
        } catch (error) {
            console.error("Error scrolling:", error);
        }
    };

    // Focus trap for keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowLeft" && canScrollLeft) {
            scroll("left");
        } else if (e.key === "ArrowRight" && canScrollRight) {
            scroll("right");
        }
    };

    return (
        <div className="max-w-7xl w-full mx-auto py-12 px-4 sm:px-6 lg:px-8 bg-coconut-cream">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
                <div>
                    <h2 className="text-2xl sm:text-3xl md:text-[36px] font-bold font-gilroy-bold text-cedar mb-2">
                        Popular Clubs
                    </h2>
                    <p className="text-gray-600 font-dmSans text-sm md:text-base mb-4 sm:mb-0">
                        Check out our most popular comedy venues
                    </p>
                </div>
                <div className="flex gap-2 self-end sm:self-auto">
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
                onKeyDown={handleKeyDown}
                tabIndex={0}
                aria-label="Popular comedy clubs carousel"
                className="flex gap-4 md:gap-6 overflow-x-auto scrollbar-hide snap-x snap-mandatory py-4 px-2"
                style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
            >
                {sortedClubs.map((dto) => {
                    const club = new Club(dto);
                    return (
                        <div
                            key={club.name}
                            className="flex-none w-[280px] sm:w-[320px] snap-start"
                        >
                            <PopularClubCard entity={JSON.stringify(club)} />
                        </div>
                    );
                })}
            </div>

            {/* Dynamic mobile scroll indicator */}
            <div className="flex justify-center mt-4 gap-1.5 sm:hidden">
                {sortedClubs.length > 0 &&
                    Array.from({
                        length: Math.ceil(sortedClubs.length / 3),
                    }).map((_, index) => (
                        <div
                            key={`indicator-${index}`}
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                                index === activeIndicator
                                    ? "w-8 bg-cedar"
                                    : "w-2 bg-gray-300"
                            }`}
                            onClick={() => {
                                // Allow clicking indicators to jump to that section
                                const container = scrollContainerRef.current;
                                if (!container) return;

                                const totalWidth =
                                    container.scrollWidth -
                                    container.clientWidth;
                                const totalIndicators = Math.ceil(
                                    sortedClubs.length / 3,
                                );
                                const targetPosition =
                                    (index / (totalIndicators - 1)) *
                                    totalWidth;

                                container.scrollTo({
                                    left: targetPosition,
                                    behavior: "smooth",
                                });
                            }}
                            role="button"
                            tabIndex={0}
                            aria-label={`Go to slide set ${index + 1}`}
                        />
                    ))}
            </div>
        </div>
    );
};

export default TrendingClubsCarousel;
