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

    const checkScrollability = () => {
        const container = scrollContainerRef.current;
        if (!container) return;

        // Get actual card width including gap
        const cardWidth = window.innerWidth >= 640 ? 320 + 16 : 280 + 16; // card width + gap
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
    };

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
    }, [isClient, sortedClubs.length]);

    const scroll = (direction: "left" | "right") => {
        const container = scrollContainerRef.current;
        if (!container) return;

        // Use actual card width
        const cardWidth = window.innerWidth >= 640 ? 320 + 16 : 280 + 16; // card width + gap
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

        const cardWidth = window.innerWidth >= 640 ? 320 + 16 : 280 + 16; // card width + gap
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
                className="flex gap-4 md:gap-6 overflow-x-auto scrollbar-hide py-4 px-2 scroll-smooth"
                style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
            >
                {sortedClubs.map((dto) => {
                    const club = new Club(dto);
                    return (
                        <div
                            key={club.name}
                            className="flex-none w-[280px] sm:w-[320px]"
                        >
                            <PopularClubCard entity={JSON.stringify(club)} />
                        </div>
                    );
                })}
            </div>

            <div className="flex justify-center mt-4 gap-1.5 sm:hidden">
                {Array.from({ length: Math.ceil(sortedClubs.length / 3) }).map(
                    (_, index) => (
                        <button
                            key={`indicator-${index}`}
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                                index === activeIndicator
                                    ? "w-8 bg-cedar"
                                    : "w-2 bg-gray-300"
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
