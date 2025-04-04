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
import { useLocationParams } from "../../hooks/useLocationParams";

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
    onDistanceSelection?: (value: string) => void;
    onZipcodeInput?: (value: string) => void;
};

type ShowLocationComponentProps =
    | ShowDistanceFormProps
    | ShowDistanceStandaloneProps;

const ShowLocationComponent = (props: ShowLocationComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const { updateDistance, updateZipCode } = useLocationParams();

    const buildDropdownComponent = (props: ShowLocationComponentProps) => {
        if (props.variant === ComponentVariant.Form) {
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
                onChange={props.onDistanceSelection ?? updateDistance}
                value={props.value?.distance ?? ""}
                variant={props.variant}
            />
        );
    };

    const buildZipCodeComponent = (props: ShowLocationComponentProps) => {
        if (props.variant === ComponentVariant.Form) {
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
                onChange={props.onZipcodeInput ?? updateZipCode}
                placeholder="Where"
                disabled={false}
            />
        );
    };

    return (
        <div className="flex flex-wrap items-center gap-4 sm:gap-6 w-full">
            <div className="flex items-center min-w-[120px] max-w-[160px]">
                <MapPin
                    className={`w-5 h-5 mr-2 flex-shrink-0 ${getCurrentStyles().iconTextColor}`}
                />
                <div className="w-full">{buildDropdownComponent(props)}</div>
            </div>

            <span
                className={`text-sm sm:text-base font-normal px-2 ${getCurrentStyles().inputTextColor} whitespace-nowrap`}
            >
                miles around
            </span>

            <div className="w-full sm:w-auto flex-1 max-w-[200px]">
                {buildZipCodeComponent(props)}
            </div>
        </div>
    );
};

export default ShowLocationComponent;
