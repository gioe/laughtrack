import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";

interface ShowTableProps {
    shows: ShowDTO[];
}

const ShowTable = ({ shows }: ShowTableProps) => {
    return (
        <section className="grid grid-cols-1 gap-y-10 m-8">
            {shows.length > 0 ? (
                shows.map((show) => {
                    return (
                        <ShowCard key={`${show.name}-${show.id}`} show={show} />
                    );
                })
            ) : (
                <div className="max-w-7xl">
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                </div>
            )}
        </section>
    );
};

export default ShowTable;
