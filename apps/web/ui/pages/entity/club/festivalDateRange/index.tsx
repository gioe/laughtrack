import { ShowDTO } from "@/objects/class/show/show.interface";
import { CalendarDays } from "lucide-react";
import { format } from "date-fns";

interface FestivalDateRangeProps {
    shows: ShowDTO[];
}

const FestivalDateRange = ({ shows }: FestivalDateRangeProps) => {
    const dates = shows
        .map((s) => new Date(s.date))
        .filter((d) => !isNaN(d.getTime()))
        .sort((a, b) => a.getTime() - b.getTime());

    if (dates.length === 0) return null;

    const earliest = dates[0];
    const latest = dates[dates.length - 1];

    const sameDay = earliest.toDateString() === latest.toDateString();
    const dateLabel = sameDay
        ? format(earliest, "MMMM d, yyyy")
        : `${format(earliest, "MMMM d")} – ${format(latest, "MMMM d, yyyy")}`;

    return (
        <div className="max-w-7xl mx-auto px-6 py-3">
            <div className="inline-flex items-center gap-2 text-sm text-gray-700">
                <CalendarDays className="w-4 h-4" />
                <span>{dateLabel}</span>
                <span className="text-gray-500">
                    · {shows.length} {shows.length === 1 ? "show" : "shows"}
                </span>
            </div>
        </div>
    );
};

export default FestivalDateRange;
