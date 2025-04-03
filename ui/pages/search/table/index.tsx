import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";

interface ShowTableProps {
    shows: ShowDTO[];
    errorMessage?: string;
}

const ShowTable = ({
    shows,
    errorMessage = "No results. Not the best search I've ever seen",
}: ShowTableProps) => {
    return (
        <section className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10 px-4 sm:px-6 md:px-8 mb-10 justify-items-start">
            {shows.length > 0 ? (
                shows.map((show) => {
                    return (
                        <ShowCard key={`${show.name}-${show.id}`} show={show} />
                    );
                })
            ) : (
                <h2 className="font-bold font-dmSans text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl text-center max-w-7xl pt-6">
                    {errorMessage}
                </h2>
            )}
        </section>
    );
};

export default ShowTable;
