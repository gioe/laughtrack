import { SortParamComponent } from "@/ui/components/params/sort";
import ShowSearchBar from "@/ui/components/searchbar";
import { Filter } from "lucide-react";

const FilterBar = () => {
    return (
        <div className="flex items-center justify-between gap-4 px-8 py-3">
            <SortParamComponent />

            {/* Filter Button */}
            <button className="flex gap-2 items-center text-[#CD7F32]">
                <Filter size={20} />
                <span className="hidden sm:inline">Filter Results</span>
            </button>
        </div>
    );
};

export default FilterBar;
