"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import ComedianHeadshot from "../image/comedian";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, useState, useEffect } from "react";

interface LineupGridProps {
    lineup: Comedian[];
}

const LineupGrid = ({ lineup }: LineupGridProps) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const [showLeftScroll, setShowLeftScroll] = useState(false);
    const [showRightScroll, setShowRightScroll] = useState(false);
    // Stop the swipe-cue pulse after 2 cycles (~4s) to avoid indefinite motion (WCAG 2.3.3)
    const [swipeCuePulsing, setSwipeCuePulsing] = useState(true);

    // Check if scrolling is needed
    const checkScroll = () => {
        if (scrollContainerRef.current) {
            const { scrollLeft, scrollWidth, clientWidth } =
                scrollContainerRef.current;
            setShowLeftScroll(scrollLeft > 0);
            setShowRightScroll(scrollLeft < scrollWidth - clientWidth - 10); // 10px buffer
        }
    };

    // Initial check and window resize handling
    useEffect(() => {
        checkScroll();
        window.addEventListener("resize", checkScroll);
        return () => window.removeEventListener("resize", checkScroll);
    }, []);

    // Stop swipe-cue pulse after 2 cycles (2 × 2s = 4s)
    useEffect(() => {
        const timer = setTimeout(() => setSwipeCuePulsing(false), 4000);
        return () => clearTimeout(timer);
    }, []);

    // Scroll handling
    const scroll = (direction: "left" | "right") => {
        if (scrollContainerRef.current) {
            const scrollAmount = scrollContainerRef.current.clientWidth * 0.75;
            scrollContainerRef.current.scrollBy({
                left: direction === "left" ? -scrollAmount : scrollAmount,
                behavior: "smooth",
            });
        }
    };

    return (
        <div className="relative group">
            {/* Scroll Container */}
            <div
                ref={scrollContainerRef}
                onScroll={checkScroll}
                className="flex gap-4 overflow-x-auto pb-4 snap-x hover:cursor-pointer scrollbar-hide"
            >
                {lineup.map((comedian, index) => (
                    <div
                        key={index}
                        className="flex-shrink-0 snap-start animate-[slideUp_500ms_ease-out,fadeIn_600ms_ease-out]"
                        style={{
                            animationDelay: `${index * 100}ms`,
                            opacity: 0,
                            animation: `slideUp 500ms ${index * 100}ms ease-out forwards, fadeIn 600ms ${index * 100}ms ease-out forwards`,
                        }}
                    >
                        <ComedianHeadshot
                            comedian={comedian}
                            variant="lineup"
                        />
                        {comedian.name.split(" ").map((nameString) => (
                            <p
                                key={nameString}
                                className="text-sm text-cedar font-semibold text-center font-dmSans text-[16px]"
                            >
                                {nameString}
                            </p>
                        ))}
                    </div>
                ))}
            </div>

            {/* Gradient Overlays */}
            {showLeftScroll && (
                <div className="absolute left-0 top-0 bottom-4 w-12 bg-gradient-to-r from-[#F5E6D3]/60 to-transparent pointer-events-none" />
            )}
            {/* Desktop: gated on scroll state */}
            {showRightScroll && (
                <div className="hidden lg:block absolute right-0 top-0 bottom-4 w-12 bg-gradient-to-l from-[#F5E6D3]/60 to-transparent pointer-events-none" />
            )}
            {/* Mobile: always-visible right gradient (gated: only when content overflows right) */}
            {showRightScroll && (
                <div className="lg:hidden absolute right-0 top-0 bottom-4 w-16 bg-gradient-to-l from-[#F5E6D3]/80 to-transparent pointer-events-none" />
            )}

            {/* Scroll Buttons */}
            {showLeftScroll && (
                <button
                    onClick={() => scroll("left")}
                    className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-white/80
                             shadow-md hover:bg-white transition-all duration-200
                             lg:opacity-0 lg:group-hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-copper"
                    aria-label="Scroll left"
                >
                    <ChevronLeft className="w-5 h-5 text-copper" />
                </button>
            )}
            {showRightScroll && (
                <button
                    onClick={() => scroll("right")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-white/80
                             shadow-md hover:bg-white transition-all duration-200
                             lg:opacity-0 lg:group-hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-copper"
                    aria-label="Scroll right"
                >
                    <ChevronRight className="w-5 h-5 text-copper" />
                </button>
            )}

            {/* Mobile swipe cue — shown before user scrolls, hidden once they start */}
            {showRightScroll && !showLeftScroll && (
                <div className={`lg:hidden absolute right-10 bottom-6 flex items-center gap-0.5 text-xs text-copper/60 pointer-events-none${swipeCuePulsing ? " animate-pulse" : ""}`}>
                    <span>swipe</span>
                    <ChevronRight className="w-3 h-3" />
                </div>
            )}
        </div>
    );
};

export default LineupGrid;
