import ShowCard from "@/components/cards/show";
import ShowSearchForm from "@/components/form/showSearch";
import { Show } from "@/objects/class/show/Show";
import {
    MapPin,
    Calendar,
    Search,
    ChevronDown,
    Filter,
    Menu,
} from "lucide-react";

interface ShowTableProps {
    shows: string;
}

const ShowTable = ({ shows }: ShowTableProps) => {
    const parsedShows = JSON.parse(shows) as Show[];

    return (
        <section className="grid grid-cols-1 gap-y-10">
            {parsedShows.length > 0 ? (
                parsedShows.map((show) => {
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
