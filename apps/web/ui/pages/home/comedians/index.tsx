import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import { Button } from "@/ui/components/ui/button";
import Link from "next/link";

interface TrendingComedianGridProps {
    comedians: ComedianDTO[];
}
const TrendingComedianGrid = ({ comedians }: TrendingComedianGridProps) => {
    return (
        <div className="max-w-7xl w-full mx-auto py-14 px-4 sm:px-6">
            <div className="mb-8 animate-fadeIn">
                <h2 className="text-3xl sm:text-4xl font-bold font-gilroy-bold mb-3 text-cedar">
                    Comics on the rise this week
                </h2>
                <p className="text-gray-600 font-dmSans text-base sm:text-lg max-w-2xl">
                    Catch the comedians showing up on more lineups right now.
                </p>
            </div>

            <div className="animate-slideUp">
                <ComedianGrid
                    comedians={comedians}
                    className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-x-4 gap-y-7"
                    isTrending={true}
                    cardVariant="compact"
                />
            </div>

            <div className="pt-10 mt-6 animate-fadeIn">
                <Button asChild variant="roundedShimmer">
                    <Link href={`/comedian/search`}>See All Comedians</Link>
                </Button>
            </div>
        </div>
    );
};

export default TrendingComedianGrid;
