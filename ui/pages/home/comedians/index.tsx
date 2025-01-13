"use server";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianCarouselCard from "@/ui/components/cards/carousel/comedian";
import Link from "next/link";

interface TrendingComedianGridProps {
    comedians: ComedianDTO[];
}
const TrendingComedianGrid = ({ comedians }: TrendingComedianGridProps) => {
    return (
        <div className="max-w-7xl mx-auto px-4 py-8">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold mb-2">Trending</h1>
                <p className="text-gray-600">
                    Catch the comedians everyone's talking about – on stage now!
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 grid-rows-2 gap-6">
                {comedians.map((dto) => {
                    const comedian = new Comedian(dto);
                    return (
                        <ComedianCarouselCard
                            key={dto.name}
                            entity={JSON.stringify(comedian)}
                        />
                    );
                })}
            </div>

            <div className="text-center mt-8">
                <Link
                    href={`/comedian/all`}
                    className="bg-[#2D1810] text-white px-6 py-3 rounded-full hover:opacity-90"
                >
                    See All Comedians
                </Link>
            </div>
        </div>
    );
};

export default TrendingComedianGrid;
