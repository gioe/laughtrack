import { SortParamComponent } from "@/ui/components/params/sort";
import { Filter } from "lucide-react";

const FilterBar = ({ children }) => {
    return (
        <div className="flex items-center justify-between gap-4 px-8 py-3">
            <SortParamComponent />
            {children}
            <button className="flex gap-2 items-center text-[#CD7F32] font-dmSans">
                <Filter size={20} />
                <span className="hidden sm:inline font">Filter Results</span>
            </button>
        </div>
    );
};

export default FilterBar;
