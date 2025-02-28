import { Input } from "@/ui/components/ui/input";
import { ChangeEvent, useCallback, useEffect, useState } from "react";
import _ from "lodash";

interface TextInputComponentProps {
    icon: React.ReactNode;
    placeholder: string;
    value?: string;
    onChange?: (value: string) => void;
    debounceTime?: number;
    className?: string;
}

const TextInputComponent = ({
    icon,
    placeholder,
    value = "",
    onChange,
    debounceTime = 500,
    className,
    ...props
}: TextInputComponentProps) => {
    const [inputValue, setInputValue] = useState(value);

    // Get the debounced value
    const debouncedOnChange = useCallback(
        _.debounce((value: string) => {
            onChange?.(value);
        }, debounceTime),
        [onChange, debounceTime],
    );

    // Update local value when prop value changes
    useEffect(() => {
        setInputValue(value);
    }, [value]);

    // Handle input changes
    const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.value;
        setInputValue(newValue);
        debouncedOnChange(newValue);
    };

    return (
        <div className="flex items-center gap-2">
            {icon}
            <Input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                placeholder={placeholder}
                {...props}
            />
        </div>
    );
};

export default TextInputComponent;
