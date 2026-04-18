"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { ShowDTO } from "@/objects/class/show/show.interface";
import CompactShowCard from "@/ui/components/cards/show/compact";
import ScrollButtons from "@/ui/components/scroll";

const CARD_WIDTH_SM = 260;
const CARD_WIDTH_MD = 300;
const CARD_GAP = 16;

interface ShowDiscoverySectionProps {
    title: string;
    subtitle: string;
    shows: ShowDTO[];
    seeAllHref: string;
}

const ShowDiscoverySection = ({
    title,
    subtitle,
    shows,
    seeAllHref,
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
            window.innerWidth >= 640
                ? CARD_WIDTH_MD + CARD_GAP
                : CARD_WIDTH_SM + CARD_GAP;
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

    return (
        <div className="max-w-7xl w-full mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row md:flex-row lg:flex-row justify-between items-start sm:items-center md:items-center lg:items-center mb-6">
                <div>
                    <h2 className="text-2xl sm:text-3xl md:text-[36px] font-bold font-gilroy-bold text-cedar mb-2">
                        {title}
                    </h2>
                    <p className="text-gray-600 font-dmSans text-sm md:text-base mb-4 sm:mb-0 md:mb-0 lg:mb-0">
                        {subtitle}
                    </p>
                </div>
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
                {shows.map((show) => (
                    <div
                        key={show.id}
                        className="flex-none w-[260px] sm:w-[300px]"
                    >
                        <CompactShowCard show={show} />
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ShowDiscoverySection;
