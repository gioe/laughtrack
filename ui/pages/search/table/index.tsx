import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";

interface ShowTableProps {
    shows: ShowDTO[];
    errorMessage?: string;
}

const ShowTable = ({
    shows,
    errorMessage = "No results. Your search is a little specific, don't you think?",
}: ShowTableProps) => {
    return (
        <section className="grid grid-cols-1 gap-y-10 m-8">
            {shows.length > 0 ? (
                shows.map((show) => {
                    return (
                        <ShowCard key={`${show.name}-${show.id}`} show={show} />
                    );
                })
            ) : (
                <h2 className="font-bold font-dmSans text-[60px] text-center max-w-7xl pt-6">
                    {errorMessage}
                </h2>
            )}
        </section>
    );
};

export default ShowTable;
