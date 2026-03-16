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
import { MapPin } from "lucide-react";

interface ZipCodeInputBaseProps {
    disabled: boolean;
    placeholder: string;
    id?: string;
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

    const inputClassName = `border-0 px-0 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0
        ${styleConfig.inputTextColor} text-sm sm:text-base
        placeholder:text-sm sm:placeholder:text-base placeholder:text-gray-400
        tracking-normal
        bg-transparent`;

    const renderInput = (value: string, onChange: (value: string) => void) => (
        <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg bg-transparent transition-colors hover:border-gray-400 focus-within:border-gray-400 focus-within:ring-2 focus-within:ring-blue-500 focus-within:outline-none">
            <MapPin
                className={`w-5 h-5 flex-shrink-0 ${styleConfig.iconTextColor}`}
            />
            <Input
                type="text"
                inputMode="numeric"
                maxLength={5}
                id={props.id}
                value={value}
                onChange={handleInputChange(onChange)}
                placeholder={props.placeholder}
                className={inputClassName}
                disabled={props.disabled}
            />
        </div>
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
