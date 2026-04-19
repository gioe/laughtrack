import Link from "next/link";
import { ShowDTO } from "@/objects/class/show/show.interface";
import CompactShowCard from "@/ui/components/cards/show/compact";

interface RelatedShowsSectionProps {
    shows: ShowDTO[];
    clubName?: string;
}

const RelatedShowsSection: React.FC<RelatedShowsSectionProps> = ({
    shows,
    clubName,
}) => {
    if (shows.length === 0) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10 mb-16">
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 mb-6">
                <h2 className="font-gilroy-bold text-[26px] font-bold text-cedar">
                    {clubName ? `More shows at ${clubName}` : "More shows"}
                </h2>
                {clubName && (
                    <Link
                        href={`/club/${clubName}`}
                        className="text-sm font-dmSans text-copper hover:underline whitespace-nowrap"
                    >
                        See all →
                    </Link>
                )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {shows.map((show) => (
                    <CompactShowCard key={show.id} show={show} />
                ))}
            </div>
        </section>
    );
};

export default RelatedShowsSection;
