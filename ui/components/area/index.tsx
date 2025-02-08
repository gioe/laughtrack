import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { UseFormReturn } from "react-hook-form";
import React from "react";
import { ShowDistanceComponentDisplay } from "./display";
import { DistanceData } from "@/util/search/util";

export enum DistanceComponentVariant {
    Form = "form",
    Standalone = "standalone",
}

interface DistanceSelectorBaseProps {
    name: string;
    icon: React.ReactNode;
}

type ShowDistanceFormProps = DistanceSelectorBaseProps & {
    variant: DistanceComponentVariant.Form;
    form: UseFormReturn<any>;
};

type ShowDistanceStandaloneProps = DistanceSelectorBaseProps & {
    variant: DistanceComponentVariant.Standalone;
    value?: DistanceData;
    onValueChange: (value: DistanceData | undefined) => void;
};

type ShowDistanceSelectionComponentProps =
    | ShowDistanceFormProps
    | ShowDistanceStandaloneProps;

const ShowDistanceSelectionComponent = (
    props: ShowDistanceSelectionComponentProps,
) => {
    if (props.variant === DistanceComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col w-full">
                        <FormControl>
                            <ShowDistanceComponentDisplay
                                selectedValues={field.value}
                                onSelect={field.onChange}
                                icon={props.icon}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    return (
        <ShowDistanceComponentDisplay
            selectedValues={props.value}
            onSelect={props.onValueChange}
            icon={props.icon}
        />
    );
};

export default ShowDistanceSelectionComponent;
