import { SortParamComponent } from "@/ui/components/params/sort";
import { Filter } from "lucide-react";

const FilterBar = ({ children }) => {
    return (
        <div className="flex items-center justify-between mx-24">
            <SortParamComponent />
            {children}
            <button className="flex gap-2 items-center text-[#CD7F32] font-dmSans">
                <Filter size={20} />
                <span className="hidden sm:inline font-dmSans text-[16px]">
                    Filter Results
                </span>
            </button>
        </div>
    );
};

export default FilterBar;
