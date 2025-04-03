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
import { useStyleContext } from "@/contexts/StyleProvider";

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

const validateZipCode = (value: string): boolean => {
    return /^\d{5}$/.test(value);
};

const ZipCodeInput = (props: ZipCodeInputComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    if (props.variant == ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => {
                    const isValid =
                        !field.value || validateZipCode(field.value);
                    return (
                        <FormItem>
                            <FormControl>
                                <Input
                                    {...field}
                                    type="text"
                                    inputMode="numeric"
                                    maxLength={5}
                                    placeholder="Where"
                                    className={`border-b border-gray-300 rounded-none px-2 py-1.5
                                             ${styleConfig.inputTextColor} text-base placeholder:text-base placeholder:text-gray-400
                                             focus:border-gray-400 hover:border-gray-400
                                             transition-colors text-center tracking-normal`}
                                    onChange={(e) => {
                                        const value = e.target.value.replace(
                                            /\D/g,
                                            "",
                                        );
                                        if (value.length <= 5) {
                                            field.onChange(value);
                                        }
                                    }}
                                />
                            </FormControl>
                            <FormMessage className="absolute text-xs mt-1" />
                        </FormItem>
                    );
                }}
            />
        );
    }

    const [inputValue, setInputValue] = useState<string | undefined>(
        props.value,
    );
    const [isValid, setIsValid] = useState(true);
    const debounceTime = props.debounceTime ?? 500;

    const debouncedOnChange = useCallback(
        _.debounce((value: string) => {
            if (!value || validateZipCode(value)) {
                props.onChange?.(value);
            }
        }, debounceTime),
        [props, debounceTime],
    );

    useEffect(() => {
        setInputValue(props.value);
        setIsValid(!props.value || validateZipCode(props.value));
    }, [props.value]);

    const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
        const value = event.target.value.replace(/\D/g, "");
        if (value.length <= 5) {
            setInputValue(value);
            setIsValid(!value || validateZipCode(value));
            debouncedOnChange(value);
        }
    };

    return (
        <Input
            type="text"
            inputMode="numeric"
            maxLength={5}
            value={inputValue}
            onChange={handleInputChange}
            placeholder="Where"
            className={`border-b border-gray-300 rounded-none px-2 py-1.5
                     ${styleConfig.inputTextColor} text-base placeholder:text-base placeholder:text-gray-400
                     focus:border-gray-400 hover:border-gray-400
                     transition-colors text-center tracking-normal`}
        />
    );
};

export default ZipCodeInput;
