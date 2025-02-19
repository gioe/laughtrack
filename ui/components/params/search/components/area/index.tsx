import { UseFormReturn } from "react-hook-form";
import React from "react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { MapPin } from "lucide-react";
import { ComponentVariant } from "@/objects/enum";
import DropdownComponent from "../dropdown";
import ZipCodeInput from "../zipcode/input";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { DistanceData } from "@/objects/interface";

const selectableDistances = allDistanceOptions.map(
    (distance: string, index: number) => ({
        id: index + 1,
        value: distance,
        display: distance,
    }),
);

type ShowDistanceFormProps = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
};

type ShowDistanceStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value: DistanceData;
    onDistanceSelection: (value: string) => void;
    onZipcodeInput: (value: string) => void;
};

type ShowLocationComponentProps =
    | ShowDistanceFormProps
    | ShowDistanceStandaloneProps;

const ShowLocationComponent = (props: ShowLocationComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const zipCodeInputClassName = `${styleConfig.searchBarTextColor}
                        text-[18px] w-40 h-9 border border-white
                        rounded-lg font-dmSans bg-transparent focus:ring-2 focus:ring-blue-500 focus:outline-none`;

    const buildDropdownComponent = (props: ShowLocationComponentProps) => {
        if (props.variant == ComponentVariant.Form) {
            return (
                <DropdownComponent
                    items={selectableDistances}
                    name="distance.distance"
                    form={props.form}
                    variant={props.variant}
                />
            );
        }

        return (
            <DropdownComponent
                items={selectableDistances}
                onChange={props.onDistanceSelection}
                value={props.value?.distance ?? ""}
                variant={props.variant}
            />
        );
    };

    const buildZipCodeComponent = (props: ShowLocationComponentProps) => {
        if (props.variant == ComponentVariant.Form) {
            return (
                <ZipCodeInput
                    variant={props.variant}
                    className={zipCodeInputClassName}
                    form={props.form}
                    placeholder="Enter a zip code"
                    disabled={false}
                    name="distance.zipCode"
                />
            );
        }

        return (
            <ZipCodeInput
                variant={props.variant}
                className={zipCodeInputClassName}
                value={props.value?.zipCode ?? ""}
                onChange={props.onZipcodeInput}
                placeholder="Enter a zip code"
                disabled={false}
            />
        );
    };

    return (
        <div className="flex items-center gap-2">
            <MapPin className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
            {buildDropdownComponent(props)}
            <div
                className={`${styleConfig.searchBarTextColor} text-[18px] font-dmSans`}
            >
                miles
            </div>
            <div
                className={`${styleConfig.searchBarTextColor} text-[18px] font-dmSans`}
            >
                around
            </div>
            <div>{buildZipCodeComponent(props)}</div>
        </div>
    );
};

export default ShowLocationComponent;
