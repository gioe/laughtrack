// ShowLocationComponent.tsx
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
        slug: distance,
        name: distance,
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
                    form={props.form}
                    placeholder="Zip code"
                    disabled={false}
                    name="distance.zipCode"
                />
            );
        }

        return (
            <ZipCodeInput
                variant={props.variant}
                value={props.value?.zipCode ?? ""}
                onChange={props.onZipcodeInput}
                placeholder="Zip code"
                disabled={false}
            />
        );
    };

    return (
        <div className="flex items-center space-x-3">
            <div className="flex items-center shrink-0 space-x-2">
                <MapPin className="w-6 h-6 text-white/70" />
                <div className="w-20">{buildDropdownComponent(props)}</div>
            </div>

            <span className="text-base font-normal text-white/70 whitespace-nowrap">
                miles around
            </span>

            <div className="w-28 shrink-0">{buildZipCodeComponent(props)}</div>
        </div>
    );
};

export default ShowLocationComponent;
