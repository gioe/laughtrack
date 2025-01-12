import ShowSearchForm from "@/components/form/showSearch";
import {
    MapPin,
    Calendar,
    Search,
    ChevronDown,
    Filter,
    Menu,
} from "lucide-react";

const FilterBar = () => {
    return (
        <div className="flex items-center justify-between gap-4 px-4 py-3">
            {/* Sort Button */}
            <button className="flex items-center gap-2 text-[#CD7F32]">
                <Menu size={20} />
                <span className="hidden sm:inline">Sort by: </span>
                <span className="hidden sm:inline">Cheapest first</span>
                <ChevronDown size={16} />
            </button>

            {/* Search Bar */}
            <div className="flex-1 max-w-2xl">
                <ShowSearchForm cities={""} />
            </div>

            {/* Filter Button */}
            <button className="flex items-center gap-2 text-[#CD7F32]">
                <Filter size={20} />
                <span className="hidden sm:inline">Filter Results</span>
            </button>
        </div>
    );
};

export default FilterBar;
