"use server";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import Link from "next/link";

interface TrendingComedianGridProps {
    comedians: ComedianDTO[];
}
const TrendingComedianGrid = ({ comedians }: TrendingComedianGridProps) => {
    return (
        <div className="max-w-7xl w-full mx-auto py-16 px-4 sm:px-6">
            <div className="text-center mb-12 animate-fadeIn">
                <h1 className="text-4xl sm:text-5xl font-bold font-gilroy-bold mb-4 text-cedar">
                    Trending Comedians
                </h1>
                <p className="text-gray-600 font-dmSans text-lg sm:text-xl max-w-2xl mx-auto">
                    Catch the comedians everyone's talking about.
                </p>
            </div>

            <div className="animate-slideUp">
                <ComedianGrid
                    comedians={comedians}
                    className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 md:gap-8"
                />
            </div>

            <div className="text-center pt-12 mt-8 animate-fadeIn">
                <Link
                    href={`/comedian/search`}
                    className="bg-[#2D1810] text-white px-8 py-4 rounded-full
                    transform transition-all duration-300 ease-in-out
                    hover:scale-105 hover:shadow-lg hover:bg-copper
                    active:scale-95 font-dmSans text-lg"
                >
                    See All Comedians
                </Link>
            </div>
        </div>
    );
};

export default TrendingComedianGrid;
