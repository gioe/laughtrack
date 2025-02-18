import { useStyleContext } from "@/contexts/StyleProvider";
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
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
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

    const textInputClassName = `${styleConfig.searchBarTextColor} 
        text-lg h-9 border border-white rounded-lg font-dmSans bg-transparent 
        focus:ring-2 focus:ring-blue-500 focus:outline-none 
        placeholder:font-dmSans placeholder:text-lg`;

    return (
        <div className="flex items-center gap-2">
            {icon}
            <div className="space-y-2">
                <Input
                    type="text"
                    className={`${textInputClassName} ${className}`}
                    value={inputValue}
                    onChange={handleInputChange}
                    placeholder={placeholder}
                    {...props}
                />
            </div>
        </div>
    );
};

export default TextInputComponent;
