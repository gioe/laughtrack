"use client";

import { Card } from "@material-tailwind/react";

const CarouselCardSkeleton = () => {
    return (
        <div className="cursor-pointer hover:scale-105 transform transition duration-300 ease-out">
            <Card className="w-96">
                <div className="h-80 rounded-full bg-gray-300 animate-pulse"></div>
                <div className="text-center bg-gray-300 animate-pulse mb-2"></div>
                <div className="flex justify-center gap-7 pt-2 bg-gray-300 animate-pulse "></div>
            </Card>
        </div>
    );
};

export default CarouselCardSkeleton;
