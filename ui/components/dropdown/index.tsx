import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { MapPin } from "lucide-react";
import { Selectable } from "@/objects/interface";
import { useStyleContext } from "@/contexts/StyleProvider";
import { UseFormReturn } from "react-hook-form";

// Base props that both variants share
interface BaseDropdownProps {
    name: string;
    placeholder: string;
    items: Selectable[];
}

// Props for the form variant
interface FormDropdownProps extends BaseDropdownProps {
    icon: React.ReactNode;
    form: UseFormReturn<any>;
    onChange?: never; // Ensure onChange is not provided with form
}

// Props for the standalone variant
interface StandaloneDropdownProps extends BaseDropdownProps {
    icon: React.ReactNode;
    form?: never; // Ensure form is not provided with onChange
    onChange: (value: string) => void;
    value?: string;
}

// Combined type using discriminated union
type DropdownProps = FormDropdownProps | StandaloneDropdownProps;

export function DropdownComponent(props: DropdownProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const baseClasses = "text-xl rounded-lg";
    const formControlClasses = `${baseClasses} lg:h-12 ${styleConfig.iconTextColor} ring-transparent focus:ring-transparent 
    shadow-none border-transparent focus:outline-none outline-none`;

    // Common wrapper for the select content
    const SelectWrapper = ({ children }: { children: React.ReactNode }) => (
        <div className="flex items-center gap-2">
            {props.icon}
            {children}
        </div>
    );

    // Render for form-controlled dropdown
    if (props.form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col">
                        <SelectWrapper>
                            <Select
                                onValueChange={field.onChange}
                                value={field.value}
                            >
                                <FormControl className={formControlClasses}>
                                    <SelectTrigger>
                                        <SelectValue
                                            className="text-left pr-2"
                                            placeholder={props.placeholder}
                                        />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent className="rounded-lg bg-white">
                                    {props.items.map((item) => (
                                        <SelectItem
                                            className="rounded-lg"
                                            key={item.id.toString()}
                                            value={item.value}
                                        >
                                            {item.display}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </SelectWrapper>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    // Render for standalone dropdown
    return (
        <SelectWrapper>
            <Select onValueChange={props.onChange} value={props.value}>
                <SelectTrigger className={formControlClasses}>
                    <SelectValue
                        className="text-left pr-2"
                        placeholder={props.placeholder}
                    />
                </SelectTrigger>
                <SelectContent className="rounded-lg bg-white">
                    {props.items.map((item) => (
                        <SelectItem
                            className="rounded-lg"
                            key={item.id.toString()}
                            value={item.value}
                        >
                            {item.display}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </SelectWrapper>
    );
}

export default DropdownComponent;
