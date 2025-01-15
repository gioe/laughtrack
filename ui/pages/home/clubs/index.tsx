"use client";

import React, { useState, useRef, useEffect } from "react";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import PopularClubCard from "@/ui/components/cards/club/card/popular";
import ScrollButtons from "@/ui/components/scroll";

interface TrendingClubsCarouselProps {
    clubs: ClubDTO[];
}

const TrendingClubsCarousel = ({ clubs }: TrendingClubsCarouselProps) => {
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [isClient, setIsClient] = useState(false);

    useEffect(() => {
        setIsClient(true);
    }, []);

    const scroll = (direction: "left" | "right") => {
        const container = scrollContainerRef.current;
        if (!container) {
            console.warn("Scroll container ref is not available");
            return;
        }

        try {
            const scrollAmount = direction === "left" ? -400 : 400;
            container.scrollTo({
                left: container.scrollLeft + scrollAmount,
                behavior: "smooth",
            });
        } catch (error) {
            console.error("Error scrolling:", error);
        }
    };

    return (
        <div className="max-w-full mx-auto px-8 py-12 bg-coconut-cream">
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h2 className="text-3xl font-bold text-[#2D1810] mb-2">
                        Popular Clubs
                    </h2>
                </div>
                <div className="flex gap-2">
                    <ScrollButtons
                        leftOnClick={() => scroll("left")}
                        rightOnClick={() => scroll("right")}
                    />
                </div>
            </div>

            <div
                ref={scrollContainerRef}
                className="flex gap-6 overflow-x-auto scrollbar-hide snap-x snap-mandatory p-10"
            >
                {clubs
                    .sort((a, b) =>
                        (a.active_comedian_count ?? 0) >
                        (b.active_comedian_count ?? 0)
                            ? -1
                            : 1,
                    )
                    .map((dto) => {
                        const club = new Club(dto);
                        return (
                            <PopularClubCard
                                key={club.name}
                                entity={JSON.stringify(club)}
                            />
                        );
                    })}
            </div>
        </div>
    );
};

export default TrendingClubsCarousel;
