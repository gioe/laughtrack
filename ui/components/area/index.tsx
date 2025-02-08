import { UseFormReturn } from "react-hook-form";
import React from "react";
import { DistanceData } from "@/util/search/util";
import { useStyleContext } from "@/contexts/StyleProvider";
import { MapPin } from "lucide-react";
import { ComponentVariant } from "@/objects/enum";

type ShowDistanceFormProps = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
    name: string;
};

type ShowDistanceStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value?: DistanceData;
    onValueChange: (value: DistanceData | undefined) => void;
};

type ShowLocationComponentProps =
    | ShowDistanceFormProps
    | ShowDistanceStandaloneProps;

const ShowLocationComponent = (props: ShowLocationComponentProps) => {
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

    return (
        <div className="flex items-center gap-2 w-full">
            <MapPin className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
            <DropdownComponent
                variant={props.variant}
                name="distance"
                items={selectableDistances}
                onChange={handleDistanceSelection}
                value={selectedValues?.distance}
            />
            <div
                className={`${styleConfig.searchBarTextColor} ${styleConfig.searchBarFontSize} font-dmSans`}
            >
                miles
            </div>
            <div
                className={`${styleConfig.searchBarTextColor} ${styleConfig.searchBarFontSize} font-dmSdmSansams`}
            >
                of
            </div>
            <div>
                <ZipCodeInput
                    variant={props.variant}
                    className={`
                        ${styleConfig.searchBarFontSize} 
                        ${styleConfig.searchBarTextColor} 
                        w-full px-3 py-2 border border-copper
                        rounded-lg focus:ring-2 font-dmSans bg-transparent`}
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

export default ShowLocationComponent;
