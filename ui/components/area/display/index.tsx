import React, { ChangeEvent } from "react";
import { DistanceData } from "@/util/search/util";
import DropdownComponent from "../../dropdown";
import ZipCodeInput from "../../input/zipcode/input";
import { useStyleContext } from "@/contexts/StyleProvider";

const selectableDistances = ["5", "10", "15", "20", "25", "50"].map(
    (distance: string, index: number) => ({
        id: index + 1,
        value: distance,
        display: distance,
    }),
);

interface ShowDistanceComponentDisplayProps {
    selectedValues?: DistanceData;
    onSelect: (value: DistanceData | undefined) => void;
    icon: React.ReactNode;
}

// Component that handles the calendar display logic
export const ShowDistanceComponentDisplay: React.FC<
    ShowDistanceComponentDisplayProps
> = ({ icon, selectedValues, onSelect }) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const handleDistanceSelection = (distance: string) => {
        onSelect({
            ...selectedValues,
            distance,
        });
    };

    const handleZipCodeInput = (event: ChangeEvent<HTMLInputElement>) => {
        onSelect({
            distance: selectedValues?.distance,
            zipCode: event.target.value,
        });
    };

    console.log(styleConfig);
    return (
        <div className="flex flex-row items-center gap-2 w-full">
            {icon}
            <span
                className={`${styleConfig.logoTextColor} text-[18px] font-dmSams`}
            >
                Within
            </span>
            <DropdownComponent
                name="distance"
                items={selectableDistances}
                onChange={handleDistanceSelection}
                value={selectedValues?.distance}
                className={`${styleConfig.searchBarFontSize} ${styleConfig.searchBarTextColor} font-dmSams rounded-lg ring-transparent focus:ring-transparent
                    shadow-none border-transparent focus:outline-none outline-none`}
            />
            <span
                className={`${styleConfig.searchBarTextColor} ${styleConfig.searchBarFontSize} font-dmSams`}
            >
                miles
            </span>
            <span
                className={`${styleConfig.searchBarTextColor} ${styleConfig.searchBarFontSize} font-dmSams`}
            >
                of
            </span>
            <div className="flex-1">
                <ZipCodeInput
                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${styleConfig.searchBarFontSize}  ${styleConfig.searchBarTextColor} font-dmSans bg-transparent`}
                    id="zip"
                    value={selectedValues?.zipCode}
                    onChange={handleZipCodeInput}
                    placeholder="Enter a zip code"
                    disabled={false}
                />
            </div>
        </div>
    );
};
