import React from "react";
import CarouselCardSkeleton from "../cards/carousel/skeleton";

export default function CarouselSkeleton() {
    return (
        <div
            className="flex space-x-3 overflow-scroll
     scrollbar-hide p-3 -ml-3"
        >
            {Array(5)
                .fill(0)
                .map((el, index) => (
                    <div key={index}>
                        <CarouselCardSkeleton />
                    </div>
                ))}
        </div>
    );
}
