import {
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from "../../../../ui/form";
import { Selectable } from "@/objects/interface";
import { UseFormReturn } from "react-hook-form";
import { ComponentVariant } from "@/objects/enum";
import DropdownDisplay from "./display";

// Base props that both variants share
interface BaseDropdownProps {
    placeholder?: string;
    items: Selectable[];
    contentId?: string;
}

// Props for the form variant
interface FormDropdownProps extends BaseDropdownProps {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
    name: string;
}

// Props for the standalone variant
interface StandaloneDropdownProps extends BaseDropdownProps {
    variant: ComponentVariant.Standalone;
    onChange: (value: string) => void;
    value?: string;
}

// Combined type using discriminated union
type DropdownProps = FormDropdownProps | StandaloneDropdownProps;

export function DropdownComponent(props: DropdownProps) {
    if (props.variant == ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col">
                        <FormControl>
                            <DropdownDisplay
                                placeholder={props.placeholder}
                                value={field.value}
                                onChange={field.onChange}
                                items={props.items}
                                contentId={props.contentId}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    return (
        <DropdownDisplay
            placeholder={props.placeholder}
            value={props.value}
            onChange={props.onChange}
            items={props.items}
            contentId={props.contentId}
        />
    );
}

export default DropdownComponent;
