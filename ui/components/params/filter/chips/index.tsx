interface FilterChipProps {
    label: string;
    selected: boolean;
    onClick: () => void;
}

export const FilterChip = ({ label, selected, onClick }: FilterChipProps) => (
    <button
        onClick={onClick}
        className={`px-4 py-2 rounded-full text-[13px] font-bold font-dmSans transition-colors
            ${
                selected
                    ? "bg-copper text-white border border-copper hover:border-white"
                    : "bg-coconut-cream text-gray-700 border border-gray-300 hover:border-copper"
            }`}
    >
        {label}
    </button>
);
