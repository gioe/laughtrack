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
            className={`px-4 py-2 rounded-full text-[13px] font-bold font-dmSans transition-colors
            ${
                option.selected
                    ? "bg-copper text-white border border-copper hover:border-white"
                    : "bg-coconut-cream text-gray-700 border border-gray-300 hover:border-copper"
            }`}
        >
            {option.name}
        </button>
    );
};
