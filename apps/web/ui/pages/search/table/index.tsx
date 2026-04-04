import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard from "@/ui/components/cards/show";
import EmptyState from "@/ui/components/emptyState";
import { Calendar, MapPin, Ticket } from "lucide-react";

interface ShowTableProps {
    shows: ShowDTO[];
    errorMessage?: string;
}

const ShowTable = ({
    shows,
    errorMessage = "Try updating your search or check back later",
}: ShowTableProps) => {
    return (
        <section className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10 px-4 sm:px-6 md:px-8 mb-10">
            {shows.length > 0 ? (
                shows.map((show) => {
                    return (
                        <ShowCard key={`${show.name}-${show.id}`} show={show} />
                    );
                })
            ) : (
                <EmptyState
                    title="No Shows Found"
                    message={errorMessage}
                    icons={[Calendar, MapPin, Ticket]}
                />
            )}
        </section>
    );
};

export default ShowTable;
