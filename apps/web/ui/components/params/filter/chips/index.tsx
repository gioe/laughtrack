import { FilterDTO } from "@/objects/interface/filter.interface";

interface FilterChipProps {
    option: FilterDTO;
    onClick: (value: string) => void;
}

export const FilterChip = ({ option, onClick }: FilterChipProps) => {
    return (
        <button
            onClick={() => {
                onClick(option.slug);
            }}
            className={`px-4 py-2 rounded-full text-[13px] font-bold font-dmSans 
            transform transition-all duration-200 ease-in-out
            shadow-sm hover:shadow-md active:scale-[0.97]
            ${
                option.selected
                    ? "bg-copper text-white border-2 border-copper hover:bg-copper/90 hover:-translate-y-[1px]"
                    : "bg-coconut-cream text-gray-700 border-2 border-gray-200 hover:border-copper/60 hover:-translate-y-[1px] hover:bg-coconut-cream/80"
            }`}
        >
            {option.name}
        </button>
    );
};
