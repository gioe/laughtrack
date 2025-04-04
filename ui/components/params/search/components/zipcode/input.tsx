import { ChangeEvent } from "react";
import { ComponentVariant } from "@/objects/enum";
import {
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from "@/ui/components/ui/form";
import { Input } from "@/ui/components/ui/input";
import { useStyleContext } from "@/contexts/StyleProvider";

interface ZipCodeInputBaseProps {
    disabled: boolean;
    placeholder: string;
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

    const handleInputChange =
        (onChange: (value: string) => void) =>
        (event: ChangeEvent<HTMLInputElement>) => {
            const value = event.target.value.replace(/\D/g, "");
            if (value.length <= 5) {
                onChange(value);
            }
        };

    const inputClassName = `border border-gray-300 rounded-lg px-2 py-1.5
                          ${styleConfig.inputTextColor} text-base placeholder:text-base placeholder:text-gray-400
                          focus:border-gray-400 hover:border-gray-400
                          transition-colors text-center tracking-normal`;

    const renderInput = (value: string, onChange: (value: string) => void) => (
        <Input
            type="text"
            inputMode="numeric"
            maxLength={5}
            value={value}
            onChange={handleInputChange(onChange)}
            placeholder="Where"
            className={inputClassName}
            disabled={props.disabled}
        />
    );

    if (props.variant === ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem>
                        <FormControl>
                            {renderInput(field.value, field.onChange)}
                        </FormControl>
                        <FormMessage className="absolute text-xs mt-1" />
                    </FormItem>
                )}
            />
        );
    }

    return renderInput(props.value ?? "", props.onChange ?? (() => {}));
};

export default ZipCodeInput;
