import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { Selectable } from "@/objects/interface";
import { UseFormReturn } from "react-hook-form";
import { useStyleContext } from "@/contexts/StyleProvider";

// Base props that both variants share
interface BaseDropdownProps {
    name: string;
    placeholder?: string;
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
    icon?: React.ReactNode;
    form?: never; // Ensure form is not provided with onChange
    onChange: (value: string) => void;
    value?: string;
}

// Combined type using discriminated union
type DropdownProps = FormDropdownProps | StandaloneDropdownProps;

export function DropdownComponent(props: DropdownProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    // Common wrapper for the select content
    const SelectWrapper = ({ children }: { children: React.ReactNode }) => (
        <div className="flex items-center">{children}</div>
    );

    if (props.form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col w-full">
                        <FormControl>
                            <SelectWrapper>
                                <Select
                                    onValueChange={field.onChange}
                                    value={field.value}
                                >
                                    <SelectTrigger
                                        className={`
                                            ${styleConfig.searchBarFontSize} ${styleConfig.searchBarTextColor}
                                            font-dmSans rounded-lg ring-transparent outline-none shadow-none border-transparent 
                                             w-full border-none focus:ring-transparent focus:outline-none focus:ring-0 focus:ring-offset-0`}
                                    >
                                        <SelectValue
                                            className="text-left"
                                            placeholder={props.placeholder}
                                        />
                                    </SelectTrigger>
                                    <SelectContent
                                        className="rounded-lg bg-white"
                                        align="start"
                                    >
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
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    return (
        <SelectWrapper>
            <Select onValueChange={props.onChange} value={props.value}>
                <SelectTrigger
                    className={`
                                            ${styleConfig.searchBarFontSize} ${styleConfig.searchBarTextColor}
                                            font-dmSans rounded-lg ring-transparent outline-none shadow-none border-transparent 
                                             w-full border-none focus:ring-transparent focus:outline-none focus:ring-0 focus:ring-offset-0`}
                >
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
