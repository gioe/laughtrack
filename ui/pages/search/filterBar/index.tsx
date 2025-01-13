import { SortParamComponent } from "@/ui/components/params/sort";
import ShowSearchBar from "@/ui/components/searchbar";
import { Filter } from "lucide-react";

const FilterBar = () => {
    return (
        <div className="flex items-center justify-between gap-4 px-4 py-3">
            <SortParamComponent />

            {/* Search Bar */}
            <div className="flex-1 max-w-2xl">
                <ShowSearchBar />
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
