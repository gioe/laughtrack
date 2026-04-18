import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";

interface PastShowsSectionProps {
    shows: ShowDTO[];
    total: number;
}

const PastShowsSection = ({ shows, total }: PastShowsSectionProps) => {
    if (total === 0) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10 mb-10">
            <h2 className="font-gilroy-bold text-[26px] font-bold text-cedar">
                Past Shows
            </h2>
            <p className="text-gray-600 font-dmSans text-[16px] mb-8">
                {total} past {total === 1 ? "show" : "shows"}
                {shows.length < total
                    ? ` — showing the ${shows.length} most recent`
                    : ""}
            </p>
            <div className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10">
                {shows.map((show) => (
                    <ShowCard key={show.id} show={show} />
                ))}
            </div>
        </section>
    );
};

export default PastShowsSection;
