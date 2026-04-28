import { ShowDTO } from "@/objects/class/show/show.interface";
import ShowCard, { ShowCardContext } from "@/ui/components/cards/show";
import EmptyState from "@/ui/components/emptyState";
import { Calendar, MapPin, Ticket } from "lucide-react";
import { ReactNode } from "react";

interface ShowTableProps {
    shows: ShowDTO[];
    errorMessage?: string;
    hideClubName?: boolean;
    emptyAction?: ReactNode;
    cardContext?: ShowCardContext;
}

const ShowTable = ({
    shows,
    errorMessage = "Try updating your search or check back later",
    hideClubName,
    emptyAction,
    cardContext,
}: ShowTableProps) => {
    return (
        <section className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10 px-4 sm:px-6 md:px-8 mb-10">
            {shows.length > 0 ? (
                shows.map((show) => {
                    return (
                        <ShowCard
                            key={show.id}
                            show={show}
                            hideClubName={hideClubName}
                            context={cardContext}
                        />
                    );
                })
            ) : (
                <EmptyState
                    title="No Shows Found"
                    message={errorMessage}
                    icons={[Calendar, MapPin, Ticket]}
                    action={emptyAction}
                />
            )}
        </section>
    );
};

export default ShowTable;
