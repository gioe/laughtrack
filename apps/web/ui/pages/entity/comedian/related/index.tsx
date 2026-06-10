import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGrid from "@/ui/components/grid/comedian";
import SectionHeader from "@/ui/components/sectionHeader";

interface RelatedComediansSectionProps {
    comedians: ComedianDTO[];
    subjectName: string;
}

const RelatedComediansSection = ({
    comedians,
    subjectName,
}: RelatedComediansSectionProps) => {
    if (comedians.length === 0) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10 mb-16">
            <SectionHeader
                eyebrow="Shared bills"
                title={`Comedians who perform with ${subjectName}`}
                subtitle="Based on shared lineups across past and upcoming shows."
                className="mb-8"
            />
            <ComedianGrid
                comedians={comedians}
                className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8"
            />
        </section>
    );
};

export default RelatedComediansSection;
