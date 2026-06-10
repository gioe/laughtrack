import { ShowDTO } from "@/objects/class/show/show.interface";
import CompactShowCard from "@/ui/components/cards/show/compact";
import SectionHeader from "@/ui/components/sectionHeader";

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
            <SectionHeader
                eyebrow="Alternates"
                title={clubName ? `More shows at ${clubName}` : "More shows"}
                actionHref={clubName ? `/club/${clubName}` : undefined}
                actionLabel={clubName ? "See all" : undefined}
                className="mb-6"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {shows.map((show) => (
                    <CompactShowCard key={show.id} show={show} />
                ))}
            </div>
        </section>
    );
};

export default RelatedShowsSection;
