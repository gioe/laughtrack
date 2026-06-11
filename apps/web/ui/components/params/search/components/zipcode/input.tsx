import { ChangeEvent } from "react";
import { FieldPath, FieldValues, UseFormReturn } from "react-hook-form";
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
    id?: string;
}

interface ZipCodeInputFormProps<TFieldValues extends FieldValues>
    extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Form;
    name: FieldPath<TFieldValues>;
    form: UseFormReturn<TFieldValues>;
}

interface ZipCodeInputStandaloneProps extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Standalone;
    onChange?: (value: string) => void;
    value?: string;
}

type ZipCodeInputComponentProps<TFieldValues extends FieldValues> =
    | ZipCodeInputFormProps<TFieldValues>
    | ZipCodeInputStandaloneProps;

const ZipCodeInput = <TFieldValues extends FieldValues>(
    props: ZipCodeInputComponentProps<TFieldValues>,
) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const handleInputChange =
        (onChange: (value: string) => void) =>
        (event: ChangeEvent<HTMLInputElement>) => {
            onChange(event.target.value);
        };

    const inputClassName = `border-0 px-0 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0
        ${styleConfig.inputTextColor} text-sm sm:text-base
        placeholder:text-sm sm:placeholder:text-base placeholder:text-muted-foreground/80
        tracking-normal
        bg-transparent`;

    const wrapperClassName =
        "flex h-9 items-center rounded-full border border-strong bg-white/5 px-3 transition-colors hover:border-copper/60 focus-within:border-copper focus-within:ring-2 focus-within:ring-copper/40 focus-within:outline-none";

    const renderInput = (value: string, onChange: (value: string) => void) => (
        <div className={wrapperClassName}>
            <Input
                type="text"
                maxLength={60}
                id={props.id}
                value={value}
                onChange={handleInputChange(onChange)}
                placeholder={props.placeholder}
                aria-label={props.placeholder}
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
