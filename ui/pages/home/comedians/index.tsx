"use server";

import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import Link from "next/link";

interface TrendingComedianGridProps {
    comedians: ComedianDTO[];
}
const TrendingComedianGrid = ({ comedians }: TrendingComedianGridProps) => {
    return (
        <div className="max-w-7xl mx-auto py-8">
            <div className="text-center mb-8">
                <h1 className="text-[36px] font-bold font-gilroy-bold mb-2 text-cedar">
                    Trending
                </h1>
                <p className="text-gray-600 font-dmSans text-[16px]">
                    Catch the comedians everyone's talking about.
                </p>
            </div>

            <ComedianGrid
                comedians={comedians}
                className="grid grid-cols-1 m:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-6"
            />

            <div className="text-center pt-8 mt-8">
                <Link
                    href={`/comedian/search`}
                    className="bg-[#2D1810] text-white px-6 py-3 rounded-full hover:opacity-90 font-dmSans"
                >
                    See All Comedians
                </Link>
            </div>
        </div>
    );
};

export default TrendingComedianGrid;
