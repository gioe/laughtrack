import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { ComponentVariant } from "@/objects/enum";
import {
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from "@/ui/components/ui/form";
import { Input } from "@/ui/components/ui/input";
import _ from "lodash";

interface ZipCodeInputBaseProps {
    disabled: boolean;
    placeholder: string;
    debounceTime?: number;
}

interface ZipCodeInputFormProps extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Form;
    name: string;
    form: any;
}

interface ZipCodeInputStandaloneProps extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Standalone;
    onChange?: (value: string) => void;
    value?: string;
}

type ZipCodeInputComponentProps =
    | ZipCodeInputFormProps
    | ZipCodeInputStandaloneProps;

const ZipCodeInput = (props: ZipCodeInputComponentProps) => {
    if (props.variant == ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => {
                    return (
                        <FormItem>
                            <FormControl className="rounded-lg">
                                <Input {...field} {...props} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    );
                }}
            />
        );
    }

    const [inputValue, setInputValue] = useState<string | undefined>(
        props.value,
    );

    const debounceTime = props.debounceTime ?? 500;

    // Get the debounced value
    const debouncedOnChange = useCallback(
        _.debounce((value: string) => {
            props.onChange?.(value);
        }, debounceTime),
        [props, debounceTime],
    );

    // Update local value when prop value changes
    useEffect(() => {
        setInputValue(props.value);
    }, [props]);

    // Handle input changes
    const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.value;
        setInputValue(newValue);
        debouncedOnChange(newValue);
    };

    return (
        <Input
            type="text"
            maxLength={5}
            pattern="[0-9]{5}"
            value={inputValue}
            onChange={handleInputChange}
            placeholder={props.placeholder}
        />
    );
};

export default ZipCodeInput;
