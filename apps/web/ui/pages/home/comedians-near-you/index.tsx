import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import { Button } from "@/ui/components/ui/button";
import Link from "next/link";

interface ComedianNearYouSectionProps {
    comedians: ComedianDTO[];
    zipCode: string;
}

const ComedianNearYouSection = ({
    comedians,
    zipCode,
}: ComedianNearYouSectionProps) => {
    if (comedians.length === 0) return null;

    return (
        <div className="max-w-7xl w-full mx-auto py-16 px-4 sm:px-6">
            <div className="text-center mb-12 animate-fadeIn">
                <h2 className="text-4xl sm:text-5xl font-bold font-gilroy-bold mb-4 text-cedar">
                    Popular Comedians Near You
                </h2>
                <p className="text-gray-600 font-dmSans text-lg sm:text-xl max-w-2xl mx-auto">
                    Comedians performing near {zipCode} — follow the ones you
                    love.
                </p>
            </div>

            <div className="animate-slideUp">
                <ComedianGrid
                    comedians={comedians}
                    className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8"
                />
            </div>

            <div className="text-center pt-12 mt-8 animate-fadeIn">
                <Button asChild variant="roundedShimmer">
                    <Link
                        href={`/show/search?zipCode=${encodeURIComponent(zipCode)}`}
                    >
                        See Shows Near You
                    </Link>
                </Button>
            </div>
        </div>
    );
};

export default ComedianNearYouSection;
